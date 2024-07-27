### 2023-02 v2.1.0

#### 1. 对phonetic symbol合法性进行检查，防止输错 P1——Done

google貌似没找到
尝试从现有meaning中提取——当前方式

#### 2. 支持修改word.text P0——Done

查出来后，修改时第一个修改的是word.text

#### 3. 支持仅修改meaning，而不重新生成ReviewPlan P0——Done

#### 4. 实现泛读复习计划 P0——Done

看到英文能知道意思就行。最看最近7天的，时间不超过5分钟
新增一个model，`ERLookupRecord`
泛读review的时候没有unremember

#### 5. 实现查询功能 P0——Done

查询works和meaning

#### 6. 模糊查询 P1——Done

**为什么只创建use_case的fts**
因为external content的fts要求所有的列必须都在同一张table中，word.text不在meaning表中，所以有额外工作：
1. 要么，将word.text添加到meaning中，word表就没有存在意义了，需要修改model
2. 要么，创建另一个fts表来存储word。
这两种方式都会带来不不小的复杂性。
考虑到use_case中肯定有word.text，因此本次只添加use_case的fts。后续重构core model的时候再重新设计。
**todo**

prototype
    修改
        `INSERT INTO meaning_fts(meaning_fts, rowid, use_case) VALUES('delete', old_meaning.id, old_meaning.use_case);`
        `INSERT INTO meaning_fts(rowid, use_case) VALUES (meaning.id, meaning.use_case);`
    添加
        `INSERT INTO meaning_fts(rowid, use_case) VALUES (meaning.id, meaning.use_case);`
    重建
        `CREATE VIRTUAL TABLE IF NOT EXISTS meaning_fts USING fts5(use_case, content='meaning', content_rowid='id', tokenize = 'porter');`
        <!-- `DROP TABLE meaning_fts;` -->
        `INSERT INTO meaning_fts(meaning_fts) VALUES('delete-all');`
        `INSERT INTO meaning_fts(rowid, use_case) select meaning.id,meaning.use_case from meaning;`
    查询

        ```sql
            select word.text,meaning.meaning,meaning.use_case FROM meaning_fts 
                LEFT JOIN meaning ON meaning_fts.rowid=meaning.id
                LEFT JOIN word ON word.id=meaning.word_id
                WHERE meaning_fts = 'beaver' order by rank limit 10;
        ```
    
initialize、migrate的时候手写sql为meaning rebuild virtual table——Done
新写入或修改meaning的时候，都先delete再插入virtual table——Done
<!-- 修改meaning的时候，删除原来的virtual table记录，插入新的记录 -->
search的时候搜索`meaning.use_case`——Done
add的时候搜索`meaning.use_case`，然后展示所有match的meaning——Pending
    因为add的时候还要判断是否有该word，所以不能只搜索use_case

https://www.sqlite.org/fts5.html#external_content_tables


#### 7. 复习计划打散 P1——Done

下一个阶段的复习计划在某个范围内打散，防止分布不均匀。
打散时间范围为`randint(0, STAGE_DELTA_MAP[stage]//6)`

#### 8. review过程升级——Done

由现在的一个一个处理，改为如下过程：
1. 先统一review，并记录每个meaning的review结果，该阶段不创建新的ReviewPlan
2. 根据review结果统一生成ReviewPlan，同一个meaning如果有多个review结果，则依次：
    * if 存在`ReviewStatus.UNREMEMBERED`
        * 则以`ReviewStatus.UNREMEMBERED`为准来生成新计划
    * else
        * if 存在`ReviewStage`最大的且结果为`ReviewStatus.REVIEWED`的ReviewPlan
            * 则以该ReviewPlan来生成新计划
        * else
            * 以`ReviewStage`最大的且结果为`ReviewStatus.REMEMBERED`的ReviewPlan
3. commit

#### 9. predict算法更新 P2——Done

目的是能够计算出更长的时间

#### 10. review过程分阶段保存，应对单词较多的情况 P1——Done

每次review，分成多组，每组5个单词。每组结束后就保存一次。

### 2022-5-4 v2.0.0
#### 实现一个单词多个含义的场景
由原来的`words->review_plans`模型，变为`words->meanings->review_plans`。
添加单词：
    1. 已存在的单词，则列出所有meanings，让user选择是否新建meanings
        如果不创建，则可以修改现有meaning
        如果创建，则新建meaning且新建review_plan
    2. 不存在的单词，则直接创建word、meaning、review_plan
复习单词：
    复习时，复习完本次review_plan的meaning之后，可以列出该word所有已存在且没有复习计划的meaning，让user选择是否复习其中一个。
        如果复习，则为该meaning建立review_plan
        如果不复习，什么都不做
        

