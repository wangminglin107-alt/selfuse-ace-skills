---
source_id: norc-gsma-method
title: GSMA Methodology Report February 2023
author: NORC at the University of Chicago
year: 2023
source_type: report
official_url: https://gss.norc.org/content/dam/gss/get-documentation/pdf/gsma/GSMA%20Methodology%20Report%20February%202023.pdf
inspected: true
---

# NORC GSMA 方法说明

## 已核验原文 {#norc-engagement-p3}

> Engagement is defined as the total number of retweets, replies, or quotes a given tweet received within 30 days of the original tweet.

位置：PDF 第 3 页，`Engagement` 段。2026-08-26 已对照页面渲染检查。

## 研究用途

这一定义固定了本试验的结果变量：它是推文发布后 30 天内的转推、回复和引用总数。报告同时说明互动不同于触达，因此不能把该指标解释成曝光人数。

## 边界与清洗提醒

- GSMA 的 VADER 正负比在负向得分总和为零时以 CSV 保留码 `888888` 表示，分析前必须排除。
- 数据按日汇总，当前研究单位不是单条推文，也不是个人。
- 来源直接定义变量，但不提供情绪与互动之间的经验结论。
