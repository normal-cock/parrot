
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
		--log-file /data00/repos/parrot/gunicorn.log \
		--timeout 120 --access-logfile - &
run_nginx:
	docker run -it --rm -d --network="host" --name parrot_nginx \
		-v /data00/repos/parrot/parrot_v2/conf/parrot_nginx.conf:/etc/nginx/conf.d/nginx_parrot.conf:ro \
		-v /data00/nginx/static:/data00/nginx/static:ro \
		-v /data00/nginx/logs:/var/log/nginx \
		nginx

reload_nginx:
	docker exec -it parrot_nginx nginx -s reload

unify_mp4_sound:
	ffmpeg -i ${PWD##*/}-raw.mp4 -af "loudnorm=I=-16:LRA=11:TP=-1" \
		-c:v copy -c:a aac -b:a 192k -y ${PWD##*/}.mp4

extract_mp3:
	ffmpeg -i ${PWD##*/}.mp4 -vn -acodec libmp3lame ${PWD##*/}.mp3

mp3_2_m3u8:
	mkdir ts_file && ffmpeg -i ${PWD##*/}.mp3 -hls_time 20 -hls_list_size 0 \
		-hls_segment_filename "ts_file/${PWD##*/}-%d.ts" \
		-hls_base_url 'ts_file/' ${PWD##*/}.m3u8

convert_subtitle_from_srt:
	cd tmp && pysubs2 --to vtt *.srt && cd -

test_cb_dict:
	python parrot_v2/dal/dict/cambridge_dict/__init__.py

poetry_install:
	poetry install

translate_vtt:
	PYTHONPATH=. python parrot_v2/dal/doubao_llm.py