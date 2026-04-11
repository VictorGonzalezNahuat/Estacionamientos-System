/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19-12.1.2-MariaDB, for osx10.21 (arm64)
--
-- Host: localhost    Database: estacionamiento
-- ------------------------------------------------------
-- Server version	12.1.2-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Table structure for table `cortes_caja`
--

DROP TABLE IF EXISTS `cortes_caja`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cortes_caja` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `id_turno` int(11) NOT NULL,
  `fecha_inicio` date NOT NULL,
  `hora_inicio` time NOT NULL,
  `fecha_fin` date NOT NULL,
  `hora_fin` time NOT NULL,
  `total_calculado` decimal(10,2) NOT NULL,
  `total_declarado` decimal(10,2) NOT NULL,
  `diferencia` decimal(10,2) NOT NULL,
  `total_efectivo` decimal(10,2) NOT NULL,
  `total_tarjeta` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `current_estacionamiento`
--

DROP TABLE IF EXISTS `current_estacionamiento`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `current_estacionamiento` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `placa` varchar(100) NOT NULL,
  `tarifa_id` int(11) NOT NULL,
  `encargado_id` int(11) NOT NULL,
  `turno_id` int(11) NOT NULL,
  `fecha_entrada` date NOT NULL,
  `hora_entrada` time NOT NULL,
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `estado_estacionamiento_unique` (`placa`)
) ENGINE=InnoDB AUTO_INCREMENT=289 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `fiscal_customers`
--

DROP TABLE IF EXISTS `fiscal_customers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `fiscal_customers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `rfc` varchar(13) NOT NULL,
  `razon_social` varchar(255) NOT NULL,
  `codigo_postal` varchar(5) NOT NULL,
  `regimen_fiscal` varchar(50) NOT NULL,
  `uso_cfdi_receptor` varchar(3) NOT NULL DEFAULT 'G03',
  `nombre_contacto` varchar(255) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `telefono` varchar(20) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `last_invoiced_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_fiscal_customers_rfc` (`rfc`),
  KEY `ix_fiscal_customers_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `history_estacionamiento`
--

DROP TABLE IF EXISTS `history_estacionamiento`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `history_estacionamiento` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tarifa_id` int(11) NOT NULL,
  `encargado_id` int(11) NOT NULL,
  `turno_id` int(11) NOT NULL,
  `fecha_entrada` date NOT NULL,
  `hora_entrada` time NOT NULL,
  `fecha_salida` date NOT NULL,
  `hora_salida` time NOT NULL,
  `placa` varchar(100) NOT NULL,
  `importe` decimal(10,2) NOT NULL,
  `metodo_pago` varchar(50) DEFAULT 'efectivo',
  `pagado` tinyint(1) DEFAULT 0,
  `payment_transaction_id` int(11) DEFAULT NULL,
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `corte_id` int(11) DEFAULT NULL,
  `facturacion_ticket_token_hash` varchar(64) DEFAULT NULL,
  `facturacion_ticket_token_expires_at` datetime DEFAULT NULL,
  `facturacion_ticket_token_upsert_used` tinyint(1) NOT NULL DEFAULT 0,
  `facturacion_ticket_token_emit_used` tinyint(1) NOT NULL DEFAULT 0,
  `facturacion_ticket_token_last_used_at` datetime DEFAULT NULL,
  `cancelado` tinyint(4) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  KEY `idx_history_metodo_pago` (`metodo_pago`),
  KEY `idx_history_pagado` (`pagado`),
  KEY `idx_history_placa_metodo` (`placa`,`metodo_pago`),
  KEY `ix_history_facturacion_ticket_token_hash` (`facturacion_ticket_token_hash`),
  KEY `ix_history_facturacion_ticket_token_expires_at` (`facturacion_ticket_token_expires_at`),
  KEY `idx_history_payment_cancelado` (`payment_transaction_id`,`cancelado`),
  KEY `idx_history_cancelado_corte` (`cancelado`,`corte_id`),
  KEY `idx_history_cancelado_fecha` (`cancelado`,`fecha_salida`),
  CONSTRAINT `1` FOREIGN KEY (`payment_transaction_id`) REFERENCES `payment_transactions` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=278 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `invoice_documents`
--

DROP TABLE IF EXISTS `invoice_documents`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `invoice_documents` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `invoice_request_id` int(11) NOT NULL,
  `uuid_fiscal` varchar(120) DEFAULT NULL,
  `serie` varchar(20) DEFAULT NULL,
  `folio` varchar(30) DEFAULT NULL,
  `issued_at` datetime DEFAULT NULL,
  `subtotal` decimal(12,2) DEFAULT NULL,
  `taxes` decimal(12,2) DEFAULT NULL,
  `total` decimal(12,2) DEFAULT NULL,
  `currency` varchar(10) NOT NULL DEFAULT 'MXN',
  `xml_url` varchar(1000) DEFAULT NULL,
  `pdf_url` varchar(1000) DEFAULT NULL,
  `verification_url` varchar(1000) DEFAULT NULL,
  `status` varchar(30) NOT NULL DEFAULT 'issued',
  `cancelled_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_invoice_documents_invoice_request_id` (`invoice_request_id`),
  KEY `ix_invoice_documents_uuid_fiscal` (`uuid_fiscal`),
  CONSTRAINT `fk_invoice_documents_invoice_request` FOREIGN KEY (`invoice_request_id`) REFERENCES `invoice_requests` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `invoice_events`
--

DROP TABLE IF EXISTS `invoice_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `invoice_events` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `invoice_request_id` int(11) NOT NULL,
  `event_type` varchar(50) NOT NULL,
  `payload_summary_json` varchar(8000) DEFAULT NULL,
  `success` tinyint(1) NOT NULL DEFAULT 1,
  `error_message` varchar(1000) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `ix_invoice_events_invoice_request_id` (`invoice_request_id`),
  KEY `ix_invoice_events_event_type` (`event_type`),
  CONSTRAINT `fk_invoice_events_invoice_request` FOREIGN KEY (`invoice_request_id`) REFERENCES `invoice_requests` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `invoice_requests`
--

DROP TABLE IF EXISTS `invoice_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `invoice_requests` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fiscal_customer_id` int(11) NOT NULL,
  `source_type` varchar(50) NOT NULL,
  `source_id` varchar(100) NOT NULL,
  `idempotency_key` varchar(255) NOT NULL,
  `status` varchar(50) NOT NULL DEFAULT 'pending',
  `total` decimal(12,2) NOT NULL,
  `currency` varchar(10) NOT NULL DEFAULT 'MXN',
  `invoice_payload_json` varchar(8000) DEFAULT NULL,
  `provider_name` varchar(50) NOT NULL DEFAULT 'facturapi',
  `provider_customer_id` varchar(255) DEFAULT NULL,
  `provider_invoice_id` varchar(255) DEFAULT NULL,
  `access_token_hash` varchar(64) DEFAULT NULL,
  `access_token_expires_at` datetime DEFAULT NULL,
  `provider_last_error` varchar(1000) DEFAULT NULL,
  `attempts` int(11) NOT NULL DEFAULT 0,
  `next_retry_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_invoice_requests_idempotency_key` (`idempotency_key`),
  KEY `ix_invoice_requests_fiscal_customer_id` (`fiscal_customer_id`),
  KEY `ix_invoice_requests_source_type` (`source_type`),
  KEY `ix_invoice_requests_source_id` (`source_id`),
  KEY `ix_invoice_requests_status` (`status`),
  KEY `ix_invoice_requests_provider_invoice_id` (`provider_invoice_id`),
  KEY `ix_invoice_requests_access_token_expires_at` (`access_token_expires_at`),
  CONSTRAINT `fk_invoice_requests_fiscal_customer` FOREIGN KEY (`fiscal_customer_id`) REFERENCES `fiscal_customers` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mensajes`
--

DROP TABLE IF EXISTS `mensajes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `mensajes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `turno_id` int(11) NOT NULL,
  `contenido` text NOT NULL,
  `admin_id` int(11) NOT NULL,
  `estado` varchar(100) DEFAULT 'pendiente',
  `fecha_enviado` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `payment_transactions`
--

DROP TABLE IF EXISTS `payment_transactions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `payment_transactions` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `preferencia_id` varchar(255) NOT NULL,
  `placa` varchar(100) NOT NULL,
  `monto` float NOT NULL,
  `estado` enum('pendiente','completado','cancelado','rechazado') DEFAULT 'pendiente',
  `metadata_mp` longtext DEFAULT NULL,
  `webhook_timestamp` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `payment_intent` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `preferencia_id` (`preferencia_id`),
  KEY `idx_preferencia_id` (`preferencia_id`),
  KEY `idx_placa` (`placa`),
  KEY `idx_estado` (`estado`),
  KEY `ix_payment_transactions_payment_intent` (`payment_intent`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `state_estacionamiento`
--

DROP TABLE IF EXISTS `state_estacionamiento`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `state_estacionamiento` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `total_espacios` int(11) NOT NULL,
  `espacios_ocupados` int(11) NOT NULL,
  `espacios_disponibles` int(11) NOT NULL,
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sync_state`
--

DROP TABLE IF EXISTS `sync_state`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `sync_state` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `table_name` varchar(100) NOT NULL,
  `last_sync_at` datetime DEFAULT NULL,
  `last_success_at` datetime DEFAULT NULL,
  `last_error` varchar(500) DEFAULT NULL,
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sync_state_table_name` (`table_name`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tarifas`
--

DROP TABLE IF EXISTS `tarifas`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tarifas` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `numero` int(11) NOT NULL,
  `tipo_vehiculo` varchar(100) DEFAULT NULL,
  `hora` decimal(10,2) NOT NULL DEFAULT 0.00,
  `fraccion` decimal(10,2) NOT NULL DEFAULT 0.00,
  `medio_dia` decimal(10,2) NOT NULL DEFAULT 0.00,
  `diario` decimal(10,2) NOT NULL DEFAULT 0.00,
  `observaciones` varchar(255) DEFAULT NULL,
  `eliminado` tinyint(1) NOT NULL DEFAULT 0,
  `default` tinyint(1) NOT NULL DEFAULT 0,
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `terminal_counters`
--

DROP TABLE IF EXISTS `terminal_counters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `terminal_counters` (
  `counter_key` varchar(64) NOT NULL,
  `current_value` bigint(20) NOT NULL DEFAULT 0,
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`counter_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `tickets_cancelados`
--

DROP TABLE IF EXISTS `tickets_cancelados`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `tickets_cancelados` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `history_estacionamiento_id` int(11) NOT NULL,
  `payment_transaction_id` int(11) DEFAULT NULL,
  `motivo` varchar(500) NOT NULL,
  `cancelado_por` int(11) NOT NULL,
  `fecha_cancelacion` datetime NOT NULL DEFAULT current_timestamp(),
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_tickets_cancelados_hist` (`history_estacionamiento_id`),
  KEY `fk_tc_payment` (`payment_transaction_id`),
  KEY `fk_tc_usuario` (`cancelado_por`),
  CONSTRAINT `fk_tc_history` FOREIGN KEY (`history_estacionamiento_id`) REFERENCES `history_estacionamiento` (`id`),
  CONSTRAINT `fk_tc_payment` FOREIGN KEY (`payment_transaction_id`) REFERENCES `payment_transactions` (`id`),
  CONSTRAINT `fk_tc_usuario` FOREIGN KEY (`cancelado_por`) REFERENCES `usuarios` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `turnos`
--

DROP TABLE IF EXISTS `turnos`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `turnos` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `encargado_id` int(11) NOT NULL,
  `fecha` date NOT NULL,
  `hora_inicio` time NOT NULL,
  `estado` varchar(100) NOT NULL,
  `hora_fin` time DEFAULT NULL,
  `fecha_fin` date DEFAULT NULL,
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=92 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `usuarios`
--

DROP TABLE IF EXISTS `usuarios`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `usuarios` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `codigo` int(11) NOT NULL,
  `nombre` varchar(200) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `comision` decimal(5,2) DEFAULT 0.00,
  `rol` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`rol`)),
  `observaciones` varchar(100) DEFAULT NULL,
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `email` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `usuarios_unique` (`codigo`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'estacionamiento'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2026-04-10 22:40:52
