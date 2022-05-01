from parrot_v2 import Session as SessionV2

from parrot_v2 import model as ModelV2


def import_data_from_v1():
    from parrot import Session as SessionV1
    from parrot import models as ModelV1
    sessionv1 = SessionV1()
    sessionv2 = SessionV2()

    added_meaning_count = 0
    added_review_plan_count = 0
    map_from_wordv1_2_meaning_v2 = {}
    for wordv1 in sessionv1.query(ModelV1.Word).all():
        wordv2 = ModelV2.Word(
            text=wordv1.text,
            created_time=wordv1.created_time,
            changed_time=wordv1.changed_time,
        )
        meaningv2 = ModelV2.Meaning(
            phonetic_symbol=wordv1.phonetic_symbol,
            meaning=wordv1.meaning,
            use_case=wordv1.use_case,
            remark=wordv1.remark,
            created_time=wordv1.created_time,
            changed_time=wordv1.changed_time,
        )
        wordv2.meanings = [
            meaningv2
        ]
        sessionv2.add(wordv2)
        sessionv2.commit()
        map_from_wordv1_2_meaning_v2[wordv1.id] = meaningv2.id
        added_meaning_count += 1

    print("{} meanings and words are added".format(added_meaning_count))

    for review_plan_v1 in sessionv1.query(ModelV1.ReviewPlan).all():
        review_type = 1
        if review_plan_v1.review_plan_type != None:
            review_type = review_plan_v1.review_plan_type.value
        review_plan_v2 = ModelV2.ReviewPlan(
            id=review_plan_v1.id,
            stage=ModelV2.ReviewStage(review_plan_v1.stage.value),
            status=ModelV2.ReviewStatus(review_plan_v1.status.value),
            review_plan_type=ModelV2.ReviewPlanType(review_type),
            time_to_review=review_plan_v1.time_to_review,
            reviewed_time=review_plan_v1.reviewed_time,
            created_time=review_plan_v1.created_time,
            changed_time=review_plan_v1.changed_time,
            meaning_id=map_from_wordv1_2_meaning_v2[review_plan_v1.word_id],
        )

        sessionv2.add(review_plan_v2)
        added_review_plan_count += 1

    sessionv2.commit()
    print("{} review plans are added".format(added_review_plan_count))
