import os
from datetime import datetime
from typing import List

import stripe
from app.db import get_session
from app.jwt import Token, create_access_token, get_current_user
from app.models import Cause, CauseForm, Donation, DonationCreate, User, UserCreate
from app.settings import Settings
from app.utils import hash_pass, verify_password
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

settings = Settings()
app = FastAPI()

templates = Jinja2Templates(directory="templates")
UPLOAD_DIRECTORY = "uploads/images/"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIRECTORY), name="uploads")


@app.get("/ping")
async def pong():
    return {"ping": "pong!"}


@app.post("/register/", response_model=User)
async def register(user: UserCreate, session: AsyncSession = Depends(get_session)):
    existing_user = await session.execute(select(User).where(User.email == user.email))
    existing_user = existing_user.first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(**user.model_dump())
    hashed_pass = hash_pass(new_user.password)
    new_user.password = hashed_pass
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


@app.post("/login/", response_model=Token)
async def register(
    user: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    existing_user = await session.execute(
        select(User).where(User.username == user.username)
    )
    existing_user = existing_user.first()
    if not existing_user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not verify_password(user.password, existing_user[0].password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"user_id": existing_user[0].id})
    return Token(access_token=access_token, token_type="bearer")


@app.post("/causes/", response_model=Cause)
async def create_cause(
    cause_data: CauseForm = Depends(CauseForm.as_form),
    session: AsyncSession = Depends(get_session),
):
    banner_image_path = os.path.join(UPLOAD_DIRECTORY, cause_data.banner_image.filename)
    with open(banner_image_path, "wb") as f:
        f.write(await cause_data.banner_image.read())

    cover_image_path = os.path.join(UPLOAD_DIRECTORY, cause_data.cover_image.filename)
    with open(cover_image_path, "wb") as f:
        f.write(await cause_data.cover_image.read())

    end_date = datetime.fromisoformat(cause_data.end_date)
    if end_date.tzinfo is not None:
        end_date = end_date.replace(tzinfo=None)

    new_cause = Cause(
        name=cause_data.name,
        tagline=cause_data.tagline,
        description=cause_data.description,
        end_date=end_date,
        banner_image=banner_image_path,
        cover_image=cover_image_path,
    )
    session.add(new_cause)
    await session.commit()
    await session.refresh(new_cause)

    return new_cause


@app.get("/causes/", response_model=List[Cause])
async def list_causes(
    session: AsyncSession = Depends(get_session),
):
    results = await session.execute(select(Cause))
    causes = results.scalars().all()
    return causes


@app.get("/donations/", response_model=List[Donation])
async def list_donations(
    session: AsyncSession = Depends(get_session),
):
    results = await session.execute(select(Donation))
    causes = results.scalars().all()
    return causes


@app.put("/causes/{cause_id}", response_model=Cause)
async def update_cause(
    cause_id: int,
    cause_data: CauseForm = Depends(CauseForm.as_form),
    session: AsyncSession = Depends(get_session),
):
    existing_cause = await session.get(Cause, cause_id)
    if not existing_cause:
        raise HTTPException(status_code=404, detail="Cause not found")

    if cause_data.banner_image:
        banner_image_path = os.path.join(
            UPLOAD_DIRECTORY, cause_data.banner_image.filename
        )
        with open(banner_image_path, "wb") as f:
            f.write(await cause_data.banner_image.read())
        existing_cause.banner_image = f"/uploads/{cause_data.banner_image.filename}"

    if cause_data.cover_image:
        cover_image_path = os.path.join(
            UPLOAD_DIRECTORY, cause_data.cover_image.filename
        )
        with open(cover_image_path, "wb") as f:
            f.write(await cause_data.cover_image.read())
        existing_cause.cover_image = f"/uploads/{cause_data.cover_image.filename}"

    existing_cause.name = cause_data.name
    existing_cause.tagline = cause_data.tagline
    existing_cause.description = cause_data.description

    end_date = datetime.fromisoformat(cause_data.end_date)
    if end_date.tzinfo is not None:
        end_date = end_date.replace(tzinfo=None)

    existing_cause.end_date = end_date

    session.add(existing_cause)
    await session.commit()
    await session.refresh(existing_cause)

    return existing_cause


@app.delete("/causes/{cause_id}", response_model=dict)
async def delete_cause(
    cause_id: int,
    session: AsyncSession = Depends(get_session),
):
    cause = await session.get(Cause, cause_id)
    if not cause:
        raise HTTPException(status_code=404, detail="Cause not found")

    await session.delete(cause)
    await session.commit()
    return {"message": "Cause deleted successfully"}


stripe.api_key = settings.STRIPE_SECRET_KEY


@app.get("/donation/payment/success", response_class=HTMLResponse)
def success_view():
    return """
    <html>
        <body>
            <h1>Payment Successful!</h1>
        </body>
    </html>
    """


@app.get("/donation/payment/cancelled", response_class=HTMLResponse)
def cancel_view():
    return """
    <html>
        <body>
            <h1>Payment Cancelled!</h1>
        </body>
    </html>
    """


@app.post("/stripe/webhook")
async def stripe_webhook(
    request: Request, session: AsyncSession = Depends(get_session)
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
    event = None

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "charge.succeeded":
        data = event["data"]["object"]["metadata"]
        amount = event["data"]["object"]["amount"]
        cause = await session.get(Cause, data["id"])
        user = await session.execute(
            select(User).where(
                User.email == event["data"]["object"]["billing_details"]["email"]
            )
        )
        user = user.first()
        user = user[0]
        if not cause or not user:
            raise HTTPException(status_code=404, detail="Cause or User not found")

        new_donation = Donation(
            donor_id=user.id,
            amount=amount / 100,
            cause_id=cause.id,
        )
        print(user, cause, new_donation)
        session.add(new_donation)
        await session.commit()

    return Response(status_code=200)


@app.get(
    "/causes/{id}/donate",
    response_class=HTMLResponse,
)
async def render_payment_ui(
    id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    cause = await session.execute(select(Cause).where(Cause.id == id))
    cause = cause.first()
    if not cause:
        raise HTTPException(status_code=404, detail="Cause not found")
    cause = cause[0]
    return templates.TemplateResponse(
        "donation_payment_ui.html",
        {
            "request": request,
            "cause": cause,
        },
    )


@app.post("/causes/{id}/create-checkout-session")
async def create_checkout_session(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    cause = await session.exec(select(Cause).where(Cause.id == id))
    cause = cause.first()
    if not cause:
        raise HTTPException(status_code=404, detail="Cause not found")

    domain_url = settings.SERVER_URL
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            success_url=f"{domain_url}/donation/payment/success",
            cancel_url=f"{domain_url}/donation/payment/cancel",
            line_items=[
                {
                    "price": "price_1QDNjALZvTUR5WIHOFYuOVUs",
                    "quantity": 1,
                }
            ],
            metadata={"cause_id": id},
        )
        return RedirectResponse(url=checkout_session.url, status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
