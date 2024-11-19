run:
	uvicorn app.main:app --reload --workers 1 --host 0.0.0.0 --port 8001
activate-win:
	..\venv\Scripts\activate
activate:
	source ../venv/Scripts/activate
makemigrations:
	alembic revision — autogenerate -m $(message)
migrate:
	alembic upgrade head
