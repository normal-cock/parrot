
makemigrations:
	mkdir -p ~/.parrot_v2
	PYTHONPATH=. alembic -c parrot_v2/alembic.ini revision --autogenerate

migrate:
	mkdir -p ~/.parrot_v2
	PYTHONPATH=. alembic -c parrot_v2/alembic.ini upgrade head

clean:
	rm -rf ~/.parrot_v2
