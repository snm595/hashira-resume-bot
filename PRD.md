Product Requirements Document (PRD)
AI Resume Screening & Candidate Ranking Bot

Version: 1.0

Platform: Telegram

Type: AI-powered Resume Screening Assistant

Development Time: 2 Hour Production MVP

1. Problem Statement

Recruiters receive hundreds of resumes for a single job opening.

Current problems include:

Manual screening takes hours.
ATS systems rely on exact keyword matching.
Candidates with transferable skills may be rejected.
Recruiters receive no explanation for rankings.
Candidates receive no feedback on improvements.
Existing systems often produce inconsistent scores for the same resume.

The objective is to build an AI-powered Telegram bot that performs intelligent resume screening, candidate ranking, explainable evaluation, and personalized learning recommendations entirely inside Telegram.

2. Product Vision

Develop an AI assistant that behaves like an experienced recruiter by:

Understanding job descriptions
Understanding resumes
Comparing candidates intelligently
Ranking candidates
Explaining every score
Suggesting improvement paths
Maintaining deterministic behavior for repeated evaluations
3. Objectives

The system must:

✓ Accept one Job Description

✓ Accept multiple resumes

✓ Compare every resume against the JD

✓ Rank candidates

✓ Explain scores

✓ Suggest missing skills

✓ Recommend learning resources

✓ Return everything inside Telegram

No web application should be required.

4. Stakeholders

Primary User

Recruiter

Secondary User

Hiring Manager

Future User

Candidate

5. User Journey
Recruiter

↓

/start

↓

Upload Job Description

↓

Upload Resume1

↓

Upload Resume2

↓

Upload Resume3

↓

Process

↓

Ranking

↓

Choose Candidate

↓

Detailed Analysis

↓

Download Report (Future)
6. Functional Requirements
FR1

Telegram Authentication

Bot should respond to

/start

Requirements

Welcome message
Instructions
Conversation state initialization
FR2

Job Description Upload

User uploads exactly one file.

Supported

PDF

DOCX

TXT

Validation

Maximum size

Allowed MIME type

Store file

FR3

Resume Upload

User uploads

1

5

20

100 resumes

Supported

PDF

DOCX

Validation

Duplicate filenames

Invalid format

Corrupted document

Store metadata

FR4

Document Parsing

Supported

PDF

DOCX

Extract

Raw text

Metadata

Pages

Encoding

Handle

Scanned PDFs (future OCR)

Corrupted files

FR5

Normalization

Normalize

Whitespace

Unicode

Capitalization

Bullet characters

Duplicate spaces

Page numbers

Headers

Footers

Purpose

Same document always produces same normalized text.

FR6

Information Extraction

Extract from Resume

Name

Email

Phone

Skills

Projects

Experience

Education

Certifications

Achievements

Extract from JD

Required Skills

Preferred Skills

Responsibilities

Experience

Education

Location

Tools

Certifications

Output JSON.

FR7

Skill Matching

Compare

JD Skills

vs

Resume Skills

Return

Matched

Missing

Additional

Similarity %

FR8

Resume Scoring

Score Components

Technical Skills

Projects

Experience

Education

Certifications

Achievements

Each section configurable.

Output

Section Score

Total Score

Confidence
FR9

LLM Evaluation

Generate

Strengths

Weaknesses

Interview readiness

Potential concerns

Hiring recommendation

Return JSON only.

FR10

Course Recommendation

Input

Missing Skills

Output

Course

Platform

Duration

Priority

Reason

FR11

Ranking

Sort candidates

Highest score first

Tie handling

Stable sorting

FR12

Candidate Report

Display

Overall Score

Matched Skills

Missing Skills

Strengths

Weaknesses

Projects

Experience Summary

Recommended Courses

Confidence Score
FR13

Telegram Interaction

Everything inside Telegram.

Commands

/start

/process

/reset

/help

User selects

1

2

3

to view report.

7. Non Functional Requirements

Performance

10 resumes

<30 seconds

100 resumes

Parallel processing

Availability

Bot should never crash.

Maintainability

Every module independent.

Scalability

Slack integration later.

Security

No permanent resume storage.

API Keys

Stored in .env

8. Architecture
Telegram

↓

Bot Layer

↓

FastAPI

↓

Upload Service

↓

Parser

↓

Normalizer

↓

Extractor

↓

Scoring Engine

↓

LLM

↓

Ranking Engine

↓

Formatter

↓

Telegram Response
9. Folder Structure
app/

bot/

api/

parser/

extractor/

normalizer/

scoring/

llm/

ranking/

recommendation/

formatter/

cache/

config/

utils/

models/

uploads/

logs/

reports/
10. Internal Modules

Upload Service

Responsible for

Saving files

Validation

Metadata

Parser

Responsible for

Reading PDFs

Reading DOCX

Normalizer

Responsible for

Cleaning text

Extractor

Responsible for

Structured JSON

Scoring Engine

Responsible for

Deterministic scoring

LLM

Responsible for

Reasoning

Ranking Engine

Responsible for

Sorting

Formatter

Responsible for

Telegram messages

11. API Design

POST

/upload/jd

POST

/upload/resume

POST

/process

GET

/candidate/{id}

POST

/reset
12. Prompt Engineering

Prompt 1

Resume Extraction

Prompt 2

JD Extraction

Prompt 3

Resume Evaluation

Prompt 4

Course Recommendation

Every prompt

Temperature

0

JSON Mode

Enabled

13. Scoring Strategy

Never ask GPT

"Give me score."

Instead

Rule Engine

Skills

40

Experience

20

Projects

20

Education

10

Certificates

10

LLM

Produces

Reasoning only.

Final

Rule Score

+

LLM Confidence Adjustment

=

Final
14. Deterministic Scoring

Requirement from problem statement

Same resume

Same JD

↓

Same score

Implementation

Normalize text

↓

Hash normalized inputs

↓

Cache

↓

Temperature = 0

↓

Fixed prompt

↓

Fixed scoring weights

15. Error Handling

Missing JD

No resumes

Unsupported format

Corrupted PDF

Parser failure

LLM timeout

Rate limiting

Telegram timeout

Every error should return a meaningful Telegram message.

16. Logging

Log

Upload

Parse

Extract

Evaluate

Rank

Respond

Every module logs independently.

17. Future Scope

Slack integration

Web Dashboard

OCR

Resume history

Analytics

Recruiter login

Candidate portal

Email reports

ATS integration

Interview scheduling

Semantic search using vector databases

18. Acceptance Criteria

The MVP is considered complete if:

A recruiter can interact entirely through Telegram.
One JD and multiple resumes can be uploaded in a single session.
PDF and DOCX files are parsed successfully.
The system extracts structured information from both the JD and resumes.
Every resume receives a deterministic, explainable score.
Candidates are ranked correctly.
A detailed report is available for each candidate.
Missing skills and course recommendations are generated.
The same resume evaluated against the same JD consistently returns the same score.
The codebase is modular, readable, and every major component can be explained and modified independently during an interview.