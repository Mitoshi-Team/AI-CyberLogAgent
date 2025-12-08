--
-- PostgreSQL database dump
--

\restrict Ih1R73LVHm9Pb4I4dMNrcBgGocxqzLgup98lf8VCPJ6NyjVa36ckFTzPl8cSAVK

-- Dumped from database version 18.1
-- Dumped by pg_dump version 18.0

-- Started on 2025-12-08 18:21:55

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
-- TOC entry 5070 (class 1262 OID 16388)
-- Name: cyber_logs_db; Type: DATABASE; Schema: -; Owner: postgres
--

-- Database is created by Docker Compose environment variables
-- CREATE DATABASE cyber_logs_db WITH TEMPLATE = template0 ENCODING = 'UTF8' LOCALE_PROVIDER = libc LOCALE = 'Russian_Russia.1251';
-- ALTER DATABASE cyber_logs_db OWNER TO postgres;

-- \unrestrict Ih1R73LVHm9Pb4I4dMNrcBgGocxqzLgup98lf8VCPJ6NyjVa36ckFTzPl8cSAVK
-- \connect cyber_logs_db
-- \restrict Ih1R73LVHm9Pb4I4dMNrcBgGocxqzLgup98lf8VCPJ6NyjVa36ckFTzPl8cSAVK

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
-- TOC entry 4 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: pg_database_owner
--

CREATE SCHEMA IF NOT EXISTS public;


ALTER SCHEMA public OWNER TO pg_database_owner;

--
-- TOC entry 5071 (class 0 OID 0)
-- Dependencies: 4
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: pg_database_owner
--

COMMENT ON SCHEMA public IS 'standard public schema';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 224 (class 1259 OID 16419)
-- Name: ActionTypes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE IF NOT EXISTS public."ActionTypes" (
    action_type_id integer NOT NULL,
    name text NOT NULL
);


ALTER TABLE public."ActionTypes" OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 16418)
-- Name: ActionTypes_action_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public."ActionTypes" ALTER COLUMN action_type_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public."ActionTypes_action_type_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 226 (class 1259 OID 16429)
-- Name: AgentLogs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE IF NOT EXISTS public."AgentLogs" (
    agent_log_id integer NOT NULL,
    action_type_id integer NOT NULL,
    description text NOT NULL,
    date timestamp with time zone NOT NULL
);


ALTER TABLE public."AgentLogs" OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 16428)
-- Name: AgentLogs_agent_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public."AgentLogs" ALTER COLUMN agent_log_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public."AgentLogs_agent_log_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 228 (class 1259 OID 16446)
-- Name: Logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE IF NOT EXISTS public."Logs" (
    log_id integer NOT NULL,
    file_content text NOT NULL,
    date timestamp with time zone NOT NULL
);


ALTER TABLE public."Logs" OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 16445)
-- Name: Logs_log_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public."Logs" ALTER COLUMN log_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public."Logs_log_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 222 (class 1259 OID 16401)
-- Name: Messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE IF NOT EXISTS public."Messages" (
    message_id integer NOT NULL,
    user_id integer NOT NULL,
    role text NOT NULL,
    content text NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public."Messages" OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 16400)
-- Name: Messages_message_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public."Messages" ALTER COLUMN message_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public."Messages_message_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 232 (class 1259 OID 16467)
-- Name: Reports; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE IF NOT EXISTS public."Reports" (
    report_id integer NOT NULL,
    description text NOT NULL,
    log_id integer NOT NULL,
    threat_type_id integer NOT NULL,
    created_at timestamp with time zone NOT NULL
);


ALTER TABLE public."Reports" OWNER TO postgres;

--
-- TOC entry 231 (class 1259 OID 16466)
-- Name: Reports_report_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public."Reports" ALTER COLUMN report_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public."Reports_report_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 230 (class 1259 OID 16457)
-- Name: ThreatTypes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE IF NOT EXISTS public."ThreatTypes" (
    threat_type_id integer NOT NULL,
    name text NOT NULL
);


ALTER TABLE public."ThreatTypes" OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 16456)
-- Name: ThreatTypes_threat_type_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public."ThreatTypes" ALTER COLUMN threat_type_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public."ThreatTypes_threat_type_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 220 (class 1259 OID 16390)
-- Name: Users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE IF NOT EXISTS public."Users" (
    user_id integer NOT NULL,
    login text NOT NULL,
    password_hash text NOT NULL
);


ALTER TABLE public."Users" OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 16389)
-- Name: Users_user_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

ALTER TABLE public."Users" ALTER COLUMN user_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public."Users_user_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- TOC entry 5056 (class 0 OID 16419)
-- Dependencies: 224
-- Data for Name: ActionTypes; Type: TABLE DATA; Schema: public; Owner: postgres
--

INSERT INTO public."ActionTypes" (action_type_id, name) OVERRIDING SYSTEM VALUE VALUES (1, 'test');


--
-- TOC entry 5058 (class 0 OID 16429)
-- Dependencies: 226
-- Data for Name: AgentLogs; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5060 (class 0 OID 16446)
-- Dependencies: 228
-- Data for Name: Logs; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5054 (class 0 OID 16401)
-- Dependencies: 222
-- Data for Name: Messages; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5064 (class 0 OID 16467)
-- Dependencies: 232
-- Data for Name: Reports; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5062 (class 0 OID 16457)
-- Dependencies: 230
-- Data for Name: ThreatTypes; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5052 (class 0 OID 16390)
-- Dependencies: 220
-- Data for Name: Users; Type: TABLE DATA; Schema: public; Owner: postgres
--



--
-- TOC entry 5072 (class 0 OID 0)
-- Dependencies: 223
-- Name: ActionTypes_action_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public."ActionTypes_action_type_id_seq"', 1, true);


--
-- TOC entry 5073 (class 0 OID 0)
-- Dependencies: 225
-- Name: AgentLogs_agent_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public."AgentLogs_agent_log_id_seq"', 1, false);


--
-- TOC entry 5074 (class 0 OID 0)
-- Dependencies: 227
-- Name: Logs_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public."Logs_log_id_seq"', 1, false);


--
-- TOC entry 5075 (class 0 OID 0)
-- Dependencies: 221
-- Name: Messages_message_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public."Messages_message_id_seq"', 1, false);


--
-- TOC entry 5076 (class 0 OID 0)
-- Dependencies: 231
-- Name: Reports_report_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public."Reports_report_id_seq"', 1, false);


--
-- TOC entry 5077 (class 0 OID 0)
-- Dependencies: 229
-- Name: ThreatTypes_threat_type_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public."ThreatTypes_threat_type_id_seq"', 1, false);


--
-- TOC entry 5078 (class 0 OID 0)
-- Dependencies: 219
-- Name: Users_user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public."Users_user_id_seq"', 1, false);


--
-- TOC entry 4891 (class 2606 OID 16427)
-- Name: ActionTypes ActionTypes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."ActionTypes"
    ADD CONSTRAINT "ActionTypes_pkey" PRIMARY KEY (action_type_id);


--
-- TOC entry 4893 (class 2606 OID 16439)
-- Name: AgentLogs AgentLogs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."AgentLogs"
    ADD CONSTRAINT "AgentLogs_pkey" PRIMARY KEY (agent_log_id);


--
-- TOC entry 4895 (class 2606 OID 16455)
-- Name: Logs Logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."Logs"
    ADD CONSTRAINT "Logs_pkey" PRIMARY KEY (log_id);


--
-- TOC entry 4889 (class 2606 OID 16412)
-- Name: Messages Messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."Messages"
    ADD CONSTRAINT "Messages_pkey" PRIMARY KEY (message_id);


--
-- TOC entry 4899 (class 2606 OID 16478)
-- Name: Reports Reports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."Reports"
    ADD CONSTRAINT "Reports_pkey" PRIMARY KEY (report_id);


--
-- TOC entry 4897 (class 2606 OID 16465)
-- Name: ThreatTypes ThreatTypes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."ThreatTypes"
    ADD CONSTRAINT "ThreatTypes_pkey" PRIMARY KEY (threat_type_id);


--
-- TOC entry 4887 (class 2606 OID 16399)
-- Name: Users Users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."Users"
    ADD CONSTRAINT "Users_pkey" PRIMARY KEY (user_id);


--
-- TOC entry 4901 (class 2606 OID 16440)
-- Name: AgentLogs FK_AgentLog_ActionType; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."AgentLogs"
    ADD CONSTRAINT "FK_AgentLog_ActionType" FOREIGN KEY (action_type_id) REFERENCES public."ActionTypes"(action_type_id);


--
-- TOC entry 4900 (class 2606 OID 16413)
-- Name: Messages FK_Message_User; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."Messages"
    ADD CONSTRAINT "FK_Message_User" FOREIGN KEY (user_id) REFERENCES public."Users"(user_id);


--
-- TOC entry 4902 (class 2606 OID 16479)
-- Name: Reports FK_Report_Log; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."Reports"
    ADD CONSTRAINT "FK_Report_Log" FOREIGN KEY (log_id) REFERENCES public."Logs"(log_id);


--
-- TOC entry 4903 (class 2606 OID 16484)
-- Name: Reports FK_Report_ThreatType; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public."Reports"
    ADD CONSTRAINT "FK_Report_ThreatType" FOREIGN KEY (threat_type_id) REFERENCES public."ThreatTypes"(threat_type_id);


-- Completed on 2025-12-08 18:21:55

--
-- PostgreSQL database dump complete
--

\unrestrict Ih1R73LVHm9Pb4I4dMNrcBgGocxqzLgup98lf8VCPJ6NyjVa36ckFTzPl8cSAVK

