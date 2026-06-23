--
-- PostgreSQL database dump
--

\restrict zi7J4daLY2QarrwhkZEy3826AM2wgpOGTSoZ2dKDgR3Q1fTfaCzJFhg2iQbQ3yl

-- Dumped from database version 18.4 (Ubuntu 18.4-0ubuntu0.26.04.1)
-- Dumped by pg_dump version 18.4 (Ubuntu 18.4-0ubuntu0.26.04.1)

-- Started on 2026-06-23 15:05:49 IST

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- TOC entry 2 (class 3079 OID 16390)
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- TOC entry 3623 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- TOC entry 883 (class 1247 OID 16422)
-- Name: admin_role; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.admin_role AS ENUM (
    'superadmin',
    'admin'
);


ALTER TYPE public.admin_role OWNER TO postgres;

--
-- TOC entry 877 (class 1247 OID 16408)
-- Name: lang_pref; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.lang_pref AS ENUM (
    'en',
    'tr'
);


ALTER TYPE public.lang_pref OWNER TO postgres;

--
-- TOC entry 880 (class 1247 OID 16414)
-- Name: sentiment_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.sentiment_type AS ENUM (
    'positive',
    'neutral',
    'negative'
);


ALTER TYPE public.sentiment_type OWNER TO postgres;

--
-- TOC entry 874 (class 1247 OID 16402)
-- Name: status_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.status_type AS ENUM (
    'active',
    'inactive'
);


ALTER TYPE public.status_type OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 222 (class 1259 OID 16457)
-- Name: admin_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.admin_users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    company_id uuid,
    name character varying NOT NULL,
    email character varying NOT NULL,
    password_hash character varying NOT NULL,
    role public.admin_role NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.admin_users OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 16427)
-- Name: companies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.companies (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying NOT NULL,
    industry character varying,
    status public.status_type DEFAULT 'active'::public.status_type,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.companies OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 16440)
-- Name: departments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.departments (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    company_id uuid,
    name character varying NOT NULL,
    min_display_count integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.departments OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 16523)
-- Name: employee_devices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.employee_devices (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    employee_id uuid,
    device_token character varying NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.employee_devices OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 16496)
-- Name: employees; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.employees (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    company_id uuid,
    department_id uuid,
    name character varying,
    email character varying NOT NULL,
    password_hash character varying NOT NULL,
    language_preference public.lang_pref DEFAULT 'en'::public.lang_pref,
    status public.status_type DEFAULT 'active'::public.status_type,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.employees OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 16597)
-- Name: feedback_answers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feedback_answers (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    submission_id uuid,
    question_id uuid,
    answer_text text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.feedback_answers OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 16582)
-- Name: feedback_keywords; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feedback_keywords (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    submission_id uuid,
    keyword character varying,
    relevance_score double precision,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.feedback_keywords OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 16618)
-- Name: feedback_sentiment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feedback_sentiment (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    submission_id uuid,
    overall_sentiment public.sentiment_type,
    sentiment_score double precision,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.feedback_sentiment OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 16540)
-- Name: feedback_submissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feedback_submissions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    company_id uuid,
    department_id uuid,
    employee_id uuid,
    date_submitted date DEFAULT CURRENT_DATE NOT NULL,
    is_anonymous boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.feedback_submissions OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 16567)
-- Name: feedback_topics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.feedback_topics (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    submission_id uuid,
    topic_label character varying,
    confidence double precision,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.feedback_topics OWNER TO postgres;

--
-- TOC entry 231 (class 1259 OID 16632)
-- Name: push_notification_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.push_notification_logs (
    department_id uuid,
    employee_count integer,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.push_notification_logs OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 16479)
-- Name: questions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.questions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    company_id uuid,
    question_text_en text,
    question_text_tr text,
    order_index integer,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.questions OWNER TO postgres;

--
-- TOC entry 3435 (class 2606 OID 16473)
-- Name: admin_users admin_users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_email_key UNIQUE (email);


--
-- TOC entry 3437 (class 2606 OID 16471)
-- Name: admin_users admin_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_pkey PRIMARY KEY (id);


--
-- TOC entry 3431 (class 2606 OID 16439)
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (id);


--
-- TOC entry 3433 (class 2606 OID 16451)
-- Name: departments departments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_pkey PRIMARY KEY (id);


--
-- TOC entry 3445 (class 2606 OID 16534)
-- Name: employee_devices employee_devices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee_devices
    ADD CONSTRAINT employee_devices_pkey PRIMARY KEY (id);


--
-- TOC entry 3441 (class 2606 OID 16512)
-- Name: employees employees_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_email_key UNIQUE (email);


--
-- TOC entry 3443 (class 2606 OID 16510)
-- Name: employees employees_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_pkey PRIMARY KEY (id);


--
-- TOC entry 3453 (class 2606 OID 16607)
-- Name: feedback_answers feedback_answers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_answers
    ADD CONSTRAINT feedback_answers_pkey PRIMARY KEY (id);


--
-- TOC entry 3451 (class 2606 OID 16591)
-- Name: feedback_keywords feedback_keywords_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_keywords
    ADD CONSTRAINT feedback_keywords_pkey PRIMARY KEY (id);


--
-- TOC entry 3455 (class 2606 OID 16626)
-- Name: feedback_sentiment feedback_sentiment_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_sentiment
    ADD CONSTRAINT feedback_sentiment_pkey PRIMARY KEY (id);


--
-- TOC entry 3447 (class 2606 OID 16551)
-- Name: feedback_submissions feedback_submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_submissions
    ADD CONSTRAINT feedback_submissions_pkey PRIMARY KEY (id);


--
-- TOC entry 3449 (class 2606 OID 16576)
-- Name: feedback_topics feedback_topics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_topics
    ADD CONSTRAINT feedback_topics_pkey PRIMARY KEY (id);


--
-- TOC entry 3439 (class 2606 OID 16490)
-- Name: questions questions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_pkey PRIMARY KEY (id);


--
-- TOC entry 3457 (class 2606 OID 16474)
-- Name: admin_users admin_users_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admin_users
    ADD CONSTRAINT admin_users_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 3456 (class 2606 OID 16452)
-- Name: departments departments_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.departments
    ADD CONSTRAINT departments_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 3461 (class 2606 OID 16535)
-- Name: employee_devices employee_devices_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee_devices
    ADD CONSTRAINT employee_devices_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id) ON DELETE CASCADE;


--
-- TOC entry 3459 (class 2606 OID 16513)
-- Name: employees employees_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 3460 (class 2606 OID 16518)
-- Name: employees employees_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employees
    ADD CONSTRAINT employees_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id) ON DELETE SET NULL;


--
-- TOC entry 3467 (class 2606 OID 16613)
-- Name: feedback_answers feedback_answers_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_answers
    ADD CONSTRAINT feedback_answers_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.questions(id) ON DELETE CASCADE;


--
-- TOC entry 3468 (class 2606 OID 16608)
-- Name: feedback_answers feedback_answers_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_answers
    ADD CONSTRAINT feedback_answers_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.feedback_submissions(id) ON DELETE CASCADE;


--
-- TOC entry 3466 (class 2606 OID 16592)
-- Name: feedback_keywords feedback_keywords_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_keywords
    ADD CONSTRAINT feedback_keywords_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.feedback_submissions(id) ON DELETE CASCADE;


--
-- TOC entry 3469 (class 2606 OID 16627)
-- Name: feedback_sentiment feedback_sentiment_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_sentiment
    ADD CONSTRAINT feedback_sentiment_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.feedback_submissions(id) ON DELETE CASCADE;


--
-- TOC entry 3462 (class 2606 OID 16552)
-- Name: feedback_submissions feedback_submissions_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_submissions
    ADD CONSTRAINT feedback_submissions_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


--
-- TOC entry 3463 (class 2606 OID 16557)
-- Name: feedback_submissions feedback_submissions_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_submissions
    ADD CONSTRAINT feedback_submissions_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id) ON DELETE SET NULL;


--
-- TOC entry 3464 (class 2606 OID 16562)
-- Name: feedback_submissions feedback_submissions_employee_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_submissions
    ADD CONSTRAINT feedback_submissions_employee_id_fkey FOREIGN KEY (employee_id) REFERENCES public.employees(id) ON DELETE SET NULL;


--
-- TOC entry 3465 (class 2606 OID 16577)
-- Name: feedback_topics feedback_topics_submission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.feedback_topics
    ADD CONSTRAINT feedback_topics_submission_id_fkey FOREIGN KEY (submission_id) REFERENCES public.feedback_submissions(id) ON DELETE CASCADE;


--
-- TOC entry 3470 (class 2606 OID 16636)
-- Name: push_notification_logs push_notification_logs_department_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.push_notification_logs
    ADD CONSTRAINT push_notification_logs_department_id_fkey FOREIGN KEY (department_id) REFERENCES public.departments(id) ON DELETE CASCADE;


--
-- TOC entry 3458 (class 2606 OID 16491)
-- Name: questions questions_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.questions
    ADD CONSTRAINT questions_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(id) ON DELETE CASCADE;


-- Completed on 2026-06-23 15:05:49 IST

--
-- PostgreSQL database dump complete
--

\unrestrict zi7J4daLY2QarrwhkZEy3826AM2wgpOGTSoZ2dKDgR3Q1fTfaCzJFhg2iQbQ3yl

