PRAGMA foreign_keys=off;

BEGIN TRANSACTION;

ALTER TABLE "review_plans" RENAME TO "review_plans_old";
CREATE TABLE IF NOT EXISTS "review_plans" (
	id INTEGER NOT NULL,
	stage VARCHAR(6),
	status VARCHAR(12),
	time_to_review DATETIME,
	reviewed_time DATETIME,
	created_time DATETIME,
	changed_time DATETIME,
	word_id INTEGER,
	PRIMARY KEY(id),
	FOREIGN KEY(word_id) REFERENCES words(id),
	CONSTRAINT reviewstage CHECK(stage IN('STAGE1', 'STAGE2', 'STAGE3', 'STAGE4', 'STAGE5')),
	CONSTRAINT reviewstatus CHECK(status IN('UNREVIEWED', 'REVIEWED', 'REMEMBERED', 'UNREMEMBERED'))
);

INSERT INTO review_plans(id, stage, status, time_to_review, reviewed_time, created_time, changed_time, word_id) 
select id, stage, status, time_to_review, reviewed_time, created_time, changed_time, word_id from review_plans_old;

COMMIT;

PRAGMA foreign_keys=on;

update alembic_version set version_num="275b21a69463";