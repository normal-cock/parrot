
makemigrations:
	mkdir -p ~/.parrot_v2
	PYTHONPATH=. alembic -c parrot_v2/alembic.ini revision --autogenerate

migrate:
	mkdir -p ~/.parrot_v2
	PYTHONPATH=. alembic -c parrot_v2/alembic.ini upgrade head

clean:
	rm -rf ~/.parrot_v2

run_test_server:
	flask --app parrot_v2.web run -h 0.0.0.0 -p 8001 --debug

run_gunicon:
	gunicorn -w 2 'parrot_v2.web:app' -b localhost:7999 --capture-output \
		--log-file /data00/open_source_project/parrot/gunicorn.log \
		--access-logfile - &
run_nginx:
	docker run -it --rm -d --network="host" --name parrot_nginx -v /data00/open_source_project/parrot/parrot_v2/conf/parrot_nginx.conf:/etc/nginx/conf.d/nginx_parrot.conf:ro nginx

extract_mp3:
	ffmpeg -i test2.mp4 -vn -acodec libmp3lame test2.mp3

convert_subtitle_from_srt:
	pysubs2 --to vtt {xxx.srt}