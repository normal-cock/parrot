
makemigrations:
	mkdir -p ~/.parrot_v2
	PYTHONPATH=. alembic -c parrot_v2/alembic.ini revision --autogenerate

migrate:
	mkdir -p ~/.parrot_v2
	PYTHONPATH=. alembic -c parrot_v2/alembic.ini upgrade head

clean:
	rm -rf ~/.parrot_v2

run_gunicon:
	nohup gunicorn -w 2 'parrot_v2.web:app' -b localhost:7999 &>> /data00/open_source_project/parrot/gunicorn.log &

run_nginx:
	docker run -it --rm -d --network="host" --name parrot_nginx -v /data00/open_source_project/parrot/parrot_v2/conf/parrot_nginx.conf:/etc/nginx/conf.d/nginx_parrot.conf:ro nginx