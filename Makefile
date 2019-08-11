
makemigrations:
	mkdir -p ~/.parrot
	PYTHONPATH=. alembic -c parrot/alembic.ini revision --autogenerate

migrate:
	mkdir -p ~/.parrot
	PYTHONPATH=. alembic -c parrot/alembic.ini upgrade head
