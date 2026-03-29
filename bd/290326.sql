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
  `hora_fin` date NOT NULL,
  `total_calculado` decimal(10,2) NOT NULL,
  `total_declarado` decimal(10,2) NOT NULL,
  `diferencia` decimal(10,2) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cortes_caja`
--

LOCK TABLES `cortes_caja` WRITE;
/*!40000 ALTER TABLE `cortes_caja` DISABLE KEYS */;
set autocommit=0;
/*!40000 ALTER TABLE `cortes_caja` ENABLE KEYS */;
UNLOCK TABLES;
commit;

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
) ENGINE=InnoDB AUTO_INCREMENT=153 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `current_estacionamiento`
--

LOCK TABLES `current_estacionamiento` WRITE;
/*!40000 ALTER TABLE `current_estacionamiento` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `current_estacionamiento` VALUES
(148,'PRUEBA1',1,2,56,'2026-03-28','20:54:04','2026-03-29 02:54:04'),
(149,'PRUEBA2',1,2,56,'2026-03-28','20:54:08','2026-03-29 02:54:08'),
(150,'PRUEBA3',1,2,56,'2026-03-28','20:54:11','2026-03-29 02:54:11'),
(151,'PRUEBA4',1,2,56,'2026-03-28','20:54:15','2026-03-29 02:54:15'),
(152,'HOLA',1,2,56,'2026-03-28','23:33:58','2026-03-29 05:33:58');
/*!40000 ALTER TABLE `current_estacionamiento` ENABLE KEYS */;
UNLOCK TABLES;
commit;

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
  PRIMARY KEY (`id`),
  KEY `payment_transaction_id` (`payment_transaction_id`),
  KEY `idx_history_metodo_pago` (`metodo_pago`),
  KEY `idx_history_pagado` (`pagado`),
  KEY `idx_history_placa_metodo` (`placa`,`metodo_pago`),
  CONSTRAINT `1` FOREIGN KEY (`payment_transaction_id`) REFERENCES `payment_transactions` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=148 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `history_estacionamiento`
--

LOCK TABLES `history_estacionamiento` WRITE;
/*!40000 ALTER TABLE `history_estacionamiento` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `history_estacionamiento` VALUES
(1,1,2,11,'2026-02-14','19:12:59','2026-02-14','21:27:45','PLACA123',75.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(2,1,2,11,'2026-02-14','21:37:31','2026-02-14','21:39:49','PRUEBA',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(3,1,2,11,'2026-02-14','22:43:07','2026-02-14','22:44:07','PRUEBBB',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(4,1,2,12,'2026-02-15','08:03:49','2026-02-15','08:06:03','UNO',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(5,1,2,12,'2026-02-15','08:05:14','2026-02-15','15:01:36','dos',210.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(6,1,2,12,'2026-02-15','08:05:45','2026-02-15','15:01:42','TRES',210.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(7,1,2,27,'2026-02-17','19:05:11','2026-02-17','20:33:13','PRUEBA',45.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(8,1,2,27,'2026-02-17','19:52:15','2026-02-17','20:33:20','PRUEBA2',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(9,1,2,27,'2026-02-17','20:44:48','2026-02-18','14:08:26','PRUEBITA',465.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(10,1,2,27,'2026-02-18','14:08:32','2026-02-18','14:09:33','PRUEBITA',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(11,1,2,27,'2026-02-18','14:00:15','2026-02-18','14:11:15','ALERTA',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(12,1,2,27,'2026-02-17','21:07:30','2026-02-18','14:11:21','PRUEBA4',465.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(13,1,2,27,'2026-02-17','21:07:24','2026-02-18','14:11:26','PRUEBA2',465.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(14,1,2,27,'2026-02-17','21:07:06','2026-02-18','14:20:19','PRUEBA1',465.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(15,1,2,27,'2026-02-17','21:07:11','2026-02-18','15:00:17','PRUEBA3',480.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(16,1,2,27,'2026-02-17','21:07:35','2026-02-18','15:00:47','PRUEBA6',480.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(17,1,2,29,'2026-02-20','16:43:58','2026-02-20','16:46:55','INGRESA',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(18,1,2,27,'2026-02-18','15:00:42','2026-02-20','22:09:41','PRUEBITA',525.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(19,1,2,31,'2026-02-21','12:06:42','2026-02-21','12:07:48','PRUEBA',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(20,1,2,27,'2026-02-20','14:45:09','2026-02-21','12:07:54','PRUEBA2',585.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(21,1,2,31,'2026-02-21','12:06:47','2026-02-21','12:07:58','PRUEBA3',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(22,1,2,31,'2026-02-21','12:06:53','2026-02-21','12:08:03','PRUEBA4',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(23,1,2,31,'2026-02-21','12:06:57','2026-02-21','12:08:07','PRUEBA5',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(24,1,2,32,'2026-02-21','23:39:00','2026-02-21','23:40:00','ZAK555F',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(25,1,2,33,'2026-02-21','23:40:39','2026-02-21','23:41:39','ZAK555F',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(26,1,2,34,'2026-02-21','23:47:01','2026-02-21','23:48:21','PRUEBITA',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(27,1,2,34,'2026-02-21','23:47:37','2026-02-23','16:44:48','PRUEBITA2',600.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(28,1,2,35,'2026-02-23','16:45:39','2026-02-23','16:58:14','PRUEBA',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(29,1,2,36,'2026-02-27','20:27:57','2026-02-27','20:32:50','PRUEBITA',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(30,1,2,36,'2026-02-23','17:03:11','2026-02-27','20:32:54','PRUEBA',705.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(31,1,2,36,'2026-02-27','20:28:02','2026-02-27','20:32:57','HOLAD',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(32,1,2,36,'2026-02-27','20:29:28','2026-02-27','20:33:00','CINCO',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(33,1,2,36,'2026-02-27','20:32:42','2026-02-28','10:11:13','HOLA',360.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(34,1,2,37,'2026-02-28','10:11:18','2026-02-28','11:04:27','2',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(35,1,2,37,'2026-02-28','10:11:16','2026-02-28','21:46:13','1',360.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(36,1,2,38,'2026-02-28','10:11:20','2026-02-28','21:57:14','3',360.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(37,1,2,40,'2026-02-28','21:57:12','2026-03-07','12:02:18','PRUEBOTA',1275.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(38,1,2,41,'2026-03-07','12:02:13','2026-03-07','12:05:52','123',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(39,3,3,44,'2026-03-07','13:20:32','2026-03-08','22:01:30','PRUEBANUEVATARI',1000.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(40,1,2,44,'2026-03-08','22:15:27','2026-03-09','21:00:27','4444',630.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(41,1,2,44,'2026-03-08','22:12:56','2026-03-09','21:45:15','123',660.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(42,1,2,44,'2026-03-08','22:15:24','2026-03-09','21:45:19','321',645.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(43,1,2,44,'2026-03-09','21:16:20','2026-03-09','21:45:21','111',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(44,1,2,44,'2026-03-09','21:16:24','2026-03-09','21:45:25','384',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(45,1,2,44,'2026-03-09','21:16:27','2026-03-09','21:45:30','564564',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(46,1,2,44,'2026-03-09','21:16:30','2026-03-09','21:45:34','HOLA',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(47,1,2,44,'2026-03-09','21:16:39','2026-03-09','21:45:38','ESTACION',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(48,1,2,44,'2026-03-09','21:44:11','2026-03-09','22:00:17','ZAK555F',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(49,1,2,44,'2026-03-09','22:00:04','2026-03-10','16:44:31','PRUEBA',510.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(50,1,2,44,'2026-03-09','21:47:24','2026-03-11','16:23:20','A1825',660.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(51,1,2,44,'2026-03-11','16:17:12','2026-03-11','16:23:30','HOLA',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(52,1,2,44,'2026-03-11','16:17:25','2026-03-11','16:23:37','PRUEBA2',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(53,1,2,44,'2026-03-11','16:21:39','2026-03-11','16:23:43','PRUEBA3',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(54,1,2,44,'2026-03-11','16:22:14','2026-03-11','16:23:50','PRUEBA',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(55,1,2,44,'2026-03-09','21:46:49','2026-03-11','16:23:59','XUC317B',660.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(56,1,2,44,'2026-03-11','16:24:10','2026-03-11','16:25:11','AAAA',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(57,1,2,47,'2026-03-11','16:24:15','2026-03-11','18:57:23','BBBB',90.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(58,1,2,47,'2026-03-11','16:24:18','2026-03-11','18:57:36','CCCC',90.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(59,1,2,47,'2026-03-11','16:24:44','2026-03-11','18:57:49','DDDD',90.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(60,1,3,47,'2026-03-11','18:57:09','2026-03-11','18:58:29','123',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(61,1,3,47,'2026-03-11','18:57:59','2026-03-12','19:00:07','9999',180.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(62,1,3,47,'2026-03-12','19:00:14','2026-03-12','19:08:10','123123',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(63,1,3,47,'2026-03-12','19:00:19','2026-03-12','19:08:27','8888',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(64,1,3,47,'2026-03-12','19:00:23','2026-03-12','19:11:04','5454',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(65,1,3,47,'2026-03-12','19:00:31','2026-03-13','07:36:52','1234567',330.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(66,1,3,48,'2026-03-12','19:08:37','2026-03-13','14:44:00','333',540.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(67,1,3,48,'2026-03-13','14:42:34','2026-03-13','14:44:06','555',30.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(68,1,3,48,'2026-03-12','19:08:18','2026-03-13','21:07:41','123123',210.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(69,1,3,49,'2026-03-13','21:39:34','2026-03-14','10:43:23','5',345.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(70,1,3,49,'2026-03-13','07:30:40','2026-03-14','12:04:06','PLACA',300.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(71,1,3,49,'2026-03-13','21:39:26','2026-03-14','12:05:46','1',375.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(72,1,3,49,'2026-03-13','07:30:56','2026-03-14','18:39:24','PLACA2',495.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(73,1,3,49,'2026-03-13','14:44:09','2026-03-14','22:20:29','555',390.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(74,1,2,49,'2026-03-14','12:05:53','2026-03-14','22:29:33','1',315.00,'efectivo',0,NULL,'2026-03-20 16:37:23'),
(75,1,2,49,'2026-03-14','22:29:35','2026-03-20','16:43:37','1',1245.00,'efectivo',0,NULL,'2026-03-20 22:43:37'),
(76,1,3,50,'2026-03-13','07:36:45','2026-03-20','16:48:17','PLACA4',1335.00,'efectivo',0,NULL,'2026-03-20 22:48:17'),
(77,1,2,50,'2026-03-20','16:55:13','2026-03-20','22:00:49','AUTOSYNC',165.00,'efectivo',0,NULL,'2026-03-21 04:00:49'),
(78,1,2,50,'2026-03-20','16:57:11','2026-03-20','22:00:54','SYNCAUTO2',165.00,'efectivo',0,NULL,'2026-03-21 04:00:54'),
(79,1,2,50,'2026-03-20','16:46:19','2026-03-20','22:01:02','SYNCNUEVO',165.00,'efectivo',0,NULL,'2026-03-21 04:01:02'),
(80,1,2,50,'2026-03-20','22:17:17','2026-03-20','22:36:48','NUEVONUEVO',30.00,'efectivo',0,NULL,'2026-03-21 04:36:48'),
(81,1,3,51,'2026-03-13','21:38:53','2026-03-21','11:00:58','999',1395.00,'efectivo',0,NULL,'2026-03-21 17:00:58'),
(82,1,3,51,'2026-03-13','21:39:28','2026-03-21','11:28:01','2',1410.00,'efectivo',0,NULL,'2026-03-21 17:28:01'),
(83,1,2,51,'2026-03-20','16:48:26','2026-03-21','11:29:41','000',510.00,'efectivo',0,NULL,'2026-03-21 17:29:41'),
(84,1,2,51,'2026-03-20','16:43:43','2026-03-21','11:29:50','PRUEBANUEVO',510.00,'efectivo',0,NULL,'2026-03-21 17:29:50'),
(85,1,2,51,'2026-03-21','11:28:40','2026-03-21','11:34:08','2',30.00,'efectivo',0,NULL,'2026-03-21 17:34:08'),
(86,1,2,51,'2026-03-21','11:28:38','2026-03-21','11:34:37','1',30.00,'efectivo',0,NULL,'2026-03-21 17:34:37'),
(87,1,3,51,'2026-03-13','21:39:30','2026-03-21','11:38:35','3',1410.00,'efectivo',0,NULL,'2026-03-21 17:38:35'),
(88,1,3,51,'2026-03-13','21:39:32','2026-03-21','11:40:13','4',1410.00,'efectivo',0,NULL,'2026-03-21 17:40:13'),
(89,1,3,51,'2026-03-13','21:39:36','2026-03-21','13:05:05','6',1455.00,'efectivo',0,NULL,'2026-03-21 19:05:05'),
(90,1,2,51,'2026-03-21','11:36:10','2026-03-21','13:05:36','2',45.00,'efectivo',0,NULL,'2026-03-21 19:05:36'),
(91,1,2,51,'2026-03-21','13:09:24','2026-03-21','13:12:22','ZAK555F',30.00,'efectivo',0,NULL,'2026-03-21 19:12:22'),
(92,1,2,51,'2026-03-21','11:29:59','2026-03-21','13:17:08','PRUEBA',60.00,'efectivo',0,NULL,'2026-03-21 19:17:08'),
(93,1,3,51,'2026-03-13','21:39:38','2026-03-21','13:24:29','7',1470.00,'efectivo',0,NULL,'2026-03-21 19:24:29'),
(94,1,2,51,'2026-03-21','13:29:54','2026-03-21','13:36:32','HOLA',30.00,'efectivo',0,NULL,'2026-03-21 19:36:32'),
(95,1,2,51,'2026-03-21','13:24:43','2026-03-21','13:36:50','SAL',30.00,'efectivo',0,NULL,'2026-03-21 19:36:50'),
(96,1,2,51,'2026-03-21','13:18:45','2026-03-21','13:38:06','QR1',30.00,'efectivo',0,NULL,'2026-03-21 19:38:06'),
(97,1,3,51,'2026-03-13','21:38:33','2026-03-21','13:39:00','123321',1470.00,'efectivo',0,NULL,'2026-03-21 19:39:00'),
(98,1,2,51,'2026-03-14','18:39:19','2026-03-21','13:39:02','123',1410.00,'efectivo',0,NULL,'2026-03-21 19:39:02'),
(99,1,2,51,'2026-03-21','13:17:20','2026-03-21','13:39:05','PRUEBA',30.00,'efectivo',0,NULL,'2026-03-21 19:39:05'),
(100,1,2,51,'2026-03-21','13:05:39','2026-03-21','13:55:30','2',30.00,'efectivo',0,NULL,'2026-03-21 19:55:30'),
(101,1,2,51,'2026-03-21','13:07:48','2026-03-21','21:43:22','123123',270.00,'efectivo',0,NULL,'2026-03-22 03:43:22'),
(102,1,2,51,'2026-03-21','13:12:27','2026-03-21','21:45:13','ZAK555F',270.00,'efectivo',0,NULL,'2026-03-22 03:45:13'),
(103,1,2,51,'2026-03-21','13:55:27','2026-03-21','21:46:38','123456',240.00,'efectivo',0,NULL,'2026-03-22 03:46:38'),
(104,1,2,51,'2026-03-21','11:36:08','2026-03-21','21:49:31','1',315.00,'efectivo',0,NULL,'2026-03-22 03:49:31'),
(105,1,2,51,'2026-03-21','13:08:44','2026-03-21','21:52:06','9',270.00,'efectivo',0,NULL,'2026-03-22 03:52:06'),
(106,1,2,51,'2026-03-21','21:47:08','2026-03-21','21:52:31','123123',30.00,'efectivo',0,NULL,'2026-03-22 03:52:31'),
(107,1,2,51,'2026-03-21','13:18:09','2026-03-21','21:52:53','PRUEBAQR',270.00,'efectivo',0,NULL,'2026-03-22 03:52:53'),
(108,1,2,51,'2026-03-21','13:36:09','2026-03-21','21:52:57','PRUEBANUEVONUEVO',255.00,'efectivo',0,NULL,'2026-03-22 03:52:57'),
(109,1,2,51,'2026-03-21','13:39:08','2026-03-21','21:53:13','PRUEBA',255.00,'efectivo',0,NULL,'2026-03-22 03:53:13'),
(110,1,2,51,'2026-03-21','13:39:26','2026-03-21','21:53:18','777',255.00,'efectivo',0,NULL,'2026-03-22 03:53:18'),
(111,1,2,51,'2026-03-21','13:38:13','2026-03-21','21:53:43','5',255.00,'efectivo',0,NULL,'2026-03-22 03:53:43'),
(112,1,2,51,'2026-03-21','21:47:34','2026-03-21','21:53:46','123456',30.00,'efectivo',0,NULL,'2026-03-22 03:53:46'),
(113,1,2,51,'2026-03-21','21:52:26','2026-03-21','21:53:49','1',30.00,'efectivo',0,NULL,'2026-03-22 03:53:49'),
(114,1,2,51,'2026-03-21','21:52:46','2026-03-21','21:55:46','2',30.00,'efectivo',0,NULL,'2026-03-22 03:55:46'),
(115,1,2,51,'2026-03-21','21:53:38','2026-03-21','21:56:34','6',30.00,'efectivo',0,NULL,'2026-03-22 03:56:34'),
(116,1,2,51,'2026-03-21','21:56:31','2026-03-22','21:41:53','123',660.00,'efectivo',0,NULL,'2026-03-23 03:41:53'),
(117,1,2,51,'2026-03-21','21:53:24','2026-03-22','21:42:12','4',660.00,'efectivo',0,NULL,'2026-03-23 03:42:12'),
(118,1,2,51,'2026-03-21','21:56:11','2026-03-23','16:05:28','1',645.00,'efectivo',0,NULL,'2026-03-23 22:05:28'),
(119,1,2,51,'2026-03-21','21:56:48','2026-03-23','16:05:45','8080',645.00,'efectivo',0,NULL,'2026-03-23 22:05:45'),
(120,1,2,51,'2026-03-23','16:05:38','2026-03-23','16:11:30','ABC',30.00,'efectivo',0,NULL,'2026-03-23 22:11:30'),
(121,1,2,51,'2026-03-23','16:05:42','2026-03-23','16:12:36','TRRES',30.00,'efectivo',0,NULL,'2026-03-23 22:12:36'),
(122,1,2,51,'2026-03-23','16:13:30','2026-03-23','16:17:38','QRQRQR',30.00,'efectivo',0,NULL,'2026-03-23 22:17:38'),
(123,1,2,51,'2026-03-23','16:54:53','2026-03-23','16:58:20','PRUEBANUEVO',30.00,'efectivo',0,NULL,'2026-03-23 22:58:20'),
(124,1,2,51,'2026-03-23','16:05:35','2026-03-23','20:51:49','10',150.00,'efectivo',0,NULL,'2026-03-24 02:51:49'),
(125,1,2,51,'2026-03-23','21:05:02','2026-03-23','21:05:18','NUEVONUEVO',30.00,'efectivo',0,NULL,'2026-03-24 03:05:18'),
(126,1,2,51,'2026-03-23','20:53:21','2026-03-23','21:05:22','1',30.00,'efectivo',0,NULL,'2026-03-24 03:05:22'),
(127,1,2,51,'2026-03-23','16:49:34','2026-03-23','21:05:26','ZAK555T',135.00,'efectivo',0,NULL,'2026-03-24 03:05:26'),
(128,1,2,51,'2026-03-24','15:58:48','2026-03-24','16:01:44','ABCABC123',30.00,'efectivo',0,NULL,'2026-03-24 22:01:44'),
(129,1,2,51,'2026-03-25','16:50:17','2026-03-25','16:50:53','NUEVONOIMP',30.00,'efectivo',0,NULL,'2026-03-25 22:50:54'),
(130,1,2,51,'2026-03-25','16:49:43','2026-03-25','16:50:58','NUEVOIMPRIME',30.00,'efectivo',0,NULL,'2026-03-25 22:50:58'),
(131,1,2,51,'2026-03-23','21:16:06','2026-03-25','16:52:55','NUEVONUEVO',690.00,'efectivo',0,NULL,'2026-03-25 22:52:55'),
(132,1,2,51,'2026-03-23','16:50:38','2026-03-25','16:53:24','PRUEBAQR5',330.00,'efectivo',0,NULL,'2026-03-25 22:53:24'),
(133,1,2,51,'2026-03-21','21:56:26','2026-03-25','16:53:57','2',960.00,'efectivo',0,NULL,'2026-03-25 22:53:57'),
(134,1,2,51,'2026-03-25','17:02:23','2026-03-25','17:02:27','ICONO',30.00,'efectivo',0,NULL,'2026-03-25 23:02:27'),
(135,1,2,51,'2026-03-26','16:55:26','2026-03-26','16:59:01','NUEVONUEVO',30.00,'efectivo',0,NULL,'2026-03-26 22:59:01'),
(136,1,2,51,'2026-03-26','16:24:27','2026-03-27','14:20:34','HOLAPLLL',600.00,'efectivo',0,NULL,'2026-03-27 20:20:34'),
(137,1,2,51,'2026-03-26','16:31:26','2026-03-27','22:23:57','PRUEBAAA',330.00,'efectivo',0,NULL,'2026-03-28 04:23:57'),
(138,1,2,51,'2026-03-26','16:57:41','2026-03-27','22:24:24','NUEVOPNG',315.00,'efectivo',0,NULL,'2026-03-28 04:24:24'),
(139,1,2,51,'2026-03-26','16:59:07','2026-03-27','22:28:14','NUEVON',315.00,'efectivo',0,NULL,'2026-03-28 04:28:14'),
(140,1,2,51,'2026-03-27','14:21:17','2026-03-27','22:29:08','123123',255.00,'efectivo',0,NULL,'2026-03-28 04:29:08'),
(141,1,2,51,'2026-03-27','14:21:20','2026-03-27','23:23:18','321312',285.00,'efectivo',0,NULL,'2026-03-28 05:23:18'),
(142,1,2,51,'2026-03-27','23:24:48','2026-03-27','23:25:00','123123',30.00,'efectivo',0,NULL,'2026-03-28 05:25:01'),
(143,1,2,51,'2026-03-27','23:26:41','2026-03-27','23:26:50','321321',30.00,'efectivo',0,NULL,'2026-03-28 05:26:50'),
(144,1,2,52,'2026-03-28','12:15:29','2026-03-28','19:06:58','312',210.00,'efectivo',0,NULL,'2026-03-29 01:06:58'),
(145,1,2,53,'2026-03-22','21:42:10','2026-03-28','19:08:06','3',1335.00,'efectivo',0,NULL,'2026-03-29 01:08:06'),
(146,1,2,54,'2026-03-28','12:12:07','2026-03-28','19:30:52','123123',225.00,'efectivo',0,NULL,'2026-03-29 01:30:52'),
(147,1,2,56,'2026-03-28','20:13:58','2026-03-28','20:40:26','123123',30.00,'efectivo',0,NULL,'2026-03-29 02:40:26');
/*!40000 ALTER TABLE `history_estacionamiento` ENABLE KEYS */;
UNLOCK TABLES;
commit;

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
-- Dumping data for table `mensajes`
--

LOCK TABLES `mensajes` WRITE;
/*!40000 ALTER TABLE `mensajes` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `mensajes` VALUES
(1,48,'Hola me escuchas',2,'pendiente','2026-03-16 12:52:45'),
(2,49,'Hola prueba, aqui mandando mensaje',2,'leido','2026-03-17 15:12:50'),
(3,49,'Hola me oyes',2,'leido','2026-03-17 15:36:55'),
(4,49,'Checa tu whats rufino',2,'leido','2026-03-17 15:37:21'),
(5,49,'Hola de nuevo',2,'leido','2026-03-17 15:38:32'),
(6,49,'Es urgente',2,'leido','2026-03-17 15:38:44'),
(7,49,'Hola noob',2,'leido','2026-03-17 15:41:48'),
(8,49,'Checa tu whats es urgente',2,'leido','2026-03-17 15:42:12'),
(9,49,'Revisa tu cel',2,'leido','2026-03-17 15:42:45'),
(10,49,'Holaholaholahola',2,'leido','2026-03-17 15:44:20'),
(11,49,'Hola',2,'leido','2026-03-17 15:44:29'),
(12,49,'Contraseña: 123',2,'leido','2026-03-17 15:46:22'),
(13,49,'Checa tu whats, es urgente',2,'leido','2026-03-17 19:30:10'),
(14,49,'Hola',2,'leido','2026-03-17 19:31:05'),
(15,49,'Cómo estas',2,'leido','2026-03-17 19:31:13'),
(16,49,'Adios',2,'leido','2026-03-17 19:31:23');
/*!40000 ALTER TABLE `mensajes` ENABLE KEYS */;
UNLOCK TABLES;
commit;

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
  PRIMARY KEY (`id`),
  UNIQUE KEY `preferencia_id` (`preferencia_id`),
  KEY `idx_preferencia_id` (`preferencia_id`),
  KEY `idx_placa` (`placa`),
  KEY `idx_estado` (`estado`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `payment_transactions`
--

LOCK TABLES `payment_transactions` WRITE;
/*!40000 ALTER TABLE `payment_transactions` DISABLE KEYS */;
set autocommit=0;
/*!40000 ALTER TABLE `payment_transactions` ENABLE KEYS */;
UNLOCK TABLES;
commit;

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
-- Dumping data for table `state_estacionamiento`
--

LOCK TABLES `state_estacionamiento` WRITE;
/*!40000 ALTER TABLE `state_estacionamiento` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `state_estacionamiento` VALUES
(1,35,5,35,'2026-03-29 05:33:58');
/*!40000 ALTER TABLE `state_estacionamiento` ENABLE KEYS */;
UNLOCK TABLES;
commit;

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
-- Dumping data for table `sync_state`
--

LOCK TABLES `sync_state` WRITE;
/*!40000 ALTER TABLE `sync_state` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `sync_state` VALUES
(1,'usuarios','2026-03-29 18:48:32','2026-03-29 18:48:32',NULL,'2026-03-29 18:48:32'),
(2,'tarifas','2026-03-29 18:48:33','2026-03-29 18:48:33',NULL,'2026-03-29 18:48:33'),
(3,'turnos','2026-03-29 18:48:33','2026-03-29 18:48:33',NULL,'2026-03-29 18:48:33'),
(4,'current_estacionamiento','2026-03-29 18:48:33','2026-03-29 18:48:33',NULL,'2026-03-29 18:48:33'),
(5,'history_estacionamiento','2026-03-29 18:48:34','2026-03-29 18:48:34',NULL,'2026-03-29 18:48:34'),
(6,'state_estacionamiento','2026-03-29 18:48:34','2026-03-29 18:48:34',NULL,'2026-03-29 18:48:34');
/*!40000 ALTER TABLE `sync_state` ENABLE KEYS */;
UNLOCK TABLES;
commit;

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
-- Dumping data for table `tarifas`
--

LOCK TABLES `tarifas` WRITE;
/*!40000 ALTER TABLE `tarifas` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `tarifas` VALUES
(1,1,'carro',30.00,15.00,300.00,150.00,'observaedit',0,1,'2026-03-20 16:33:53'),
(2,2,'Carro 2',15.00,7.00,100.00,200.00,'ex Tarifa de motooooo',0,0,'2026-03-20 16:33:53'),
(3,3,'carro3',100.00,100.00,100.00,100.00,'pruebota',0,0,'2026-03-20 16:33:53'),
(4,4,'Carro confirma',12.00,122.00,12.00,12.00,'Prueba de confirmacion contraseñaasd',0,0,'2026-03-27 21:26:06');
/*!40000 ALTER TABLE `tarifas` ENABLE KEYS */;
UNLOCK TABLES;
commit;

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
) ENGINE=InnoDB AUTO_INCREMENT=58 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `turnos`
--

LOCK TABLES `turnos` WRITE;
/*!40000 ALTER TABLE `turnos` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `turnos` VALUES
(6,1,'2026-02-14','10:44:52','cerrado','10:45:15',NULL,'2026-03-20 16:43:14'),
(7,1,'2026-02-14','10:47:50','cerrado','10:48:07',NULL,'2026-03-20 16:43:14'),
(8,2,'2026-02-14','11:28:35','cerrado','11:42:43',NULL,'2026-03-20 16:43:14'),
(9,2,'2026-02-14','11:44:38','cerrado','11:44:51',NULL,'2026-03-20 16:43:14'),
(10,2,'2026-02-14','12:04:28','cerrado','12:06:02',NULL,'2026-03-20 16:43:14'),
(11,2,'2026-02-14','19:12:52','cerrado','22:44:15',NULL,'2026-03-20 16:43:14'),
(12,2,'2026-02-15','08:03:37','cerrado','15:01:56','2026-02-15','2026-03-20 16:43:14'),
(13,2,'2026-02-16','18:59:29','cerrado','19:04:33','2026-02-16','2026-03-20 16:43:14'),
(14,2,'2026-02-16','19:04:44','cerrado','19:06:23','2026-02-16','2026-03-20 16:43:14'),
(15,2,'2026-02-16','19:06:29','cerrado','19:07:22','2026-02-16','2026-03-20 16:43:14'),
(16,2,'2026-02-16','19:07:33','cerrado','19:10:13','2026-02-16','2026-03-20 16:43:14'),
(17,2,'2026-02-16','19:10:17','cerrado','19:11:24','2026-02-16','2026-03-20 16:43:14'),
(18,2,'2026-02-16','19:11:32','cerrado','19:11:41','2026-02-16','2026-03-20 16:43:14'),
(19,2,'2026-02-16','19:12:03','cerrado','20:03:01','2026-02-16','2026-03-20 16:43:14'),
(20,2,'2026-02-16','20:03:17','cerrado','20:05:51','2026-02-16','2026-03-20 16:43:14'),
(21,2,'2026-02-16','20:07:52','cerrado','20:49:43','2026-02-16','2026-03-20 16:43:14'),
(22,2,'2026-02-17','10:48:22','cerrado','10:49:25','2026-02-17','2026-03-20 16:43:14'),
(23,2,'2026-02-17','11:06:50','cerrado','14:15:30','2026-02-17','2026-03-20 16:43:14'),
(24,2,'2026-02-17','14:16:06','cerrado','17:17:56','2026-02-17','2026-03-20 16:43:14'),
(25,2,'2026-02-17','17:19:44','cerrado','17:59:31','2026-02-17','2026-03-20 16:43:14'),
(26,2,'2026-02-17','18:20:27','cerrado','18:20:56','2026-02-17','2026-03-20 16:43:14'),
(27,2,'2026-02-17','19:04:22','cerrado','14:45:20','2026-02-20','2026-03-20 16:43:14'),
(28,2,'2026-02-20','14:46:25','cerrado','14:49:55','2026-02-20','2026-03-20 16:43:14'),
(29,2,'2026-02-20','14:53:08','cerrado','20:52:50','2026-02-20','2026-03-20 16:43:14'),
(30,2,'2026-02-20','20:53:32','cerrado','09:36:23','2026-02-21','2026-03-20 16:43:14'),
(31,2,'2026-02-21','12:06:36','cerrado','12:08:22','2026-02-21','2026-03-20 16:43:14'),
(32,2,'2026-02-21','23:38:45','cerrado','23:40:11','2026-02-21','2026-03-20 16:43:14'),
(33,2,'2026-02-21','23:40:34','cerrado','23:41:55','2026-02-21','2026-03-20 16:43:14'),
(34,2,'2026-02-21','23:46:54','cerrado','23:48:33','2026-02-21','2026-03-20 16:43:14'),
(35,2,'2026-02-23','16:44:39','cerrado','16:55:36','2026-02-23','2026-03-20 16:43:14'),
(36,2,'2026-02-23','16:58:09','cerrado','21:44:43','2026-02-27','2026-03-20 16:43:14'),
(37,2,'2026-02-28','10:11:04','cerrado','21:45:50','2026-02-28','2026-03-20 16:43:14'),
(38,2,'2026-02-28','21:45:59','cerrado','13:40:45','2026-03-06','2026-03-20 16:43:14'),
(39,2,'2026-03-06','13:40:51','cerrado','12:01:38','2026-03-07','2026-03-20 16:43:14'),
(40,2,'2026-03-07','12:01:46','cerrado','12:05:12','2026-03-07','2026-03-20 16:43:14'),
(41,2,'2026-03-07','12:05:38','cerrado','12:06:00','2026-03-07','2026-03-20 16:43:14'),
(42,2,'2026-03-07','12:56:26','cerrado','21:58:49','2026-03-08','2026-03-20 16:43:14'),
(43,3,'2026-03-07','13:20:03','cerrado','22:00:36','2026-03-09','2026-03-20 16:43:14'),
(44,2,'2026-03-08','22:00:31','cerrado','16:29:05','2026-03-11','2026-03-20 16:43:14'),
(45,2,'2026-03-11','16:31:36','cerrado','16:31:54','2026-03-11','2026-03-20 16:43:14'),
(46,3,'2026-03-11','16:32:28','cerrado','16:33:04','2026-03-11','2026-03-20 16:43:14'),
(47,3,'2026-03-11','18:56:27','cerrado','07:37:11','2026-03-13','2026-03-20 16:43:14'),
(48,3,'2026-03-13','07:37:19','cerrado','21:08:33','2026-03-18','2026-03-20 16:43:14'),
(49,2,'2026-03-13','21:15:16','cerrado','16:47:59','2026-03-20','2026-03-20 22:47:59'),
(50,2,'2026-03-20','16:48:10','cerrado','22:37:58','2026-03-20','2026-03-21 04:37:58'),
(51,2,'2026-03-20','22:38:07','cerrado','19:01:42','2026-03-28','2026-03-29 01:01:42'),
(52,2,'2026-03-28','19:01:51','cerrado','19:07:25','2026-03-28','2026-03-29 01:07:25'),
(53,2,'2026-03-28','19:07:32','cerrado','19:08:37','2026-03-28','2026-03-29 01:08:37'),
(54,2,'2026-03-28','19:08:42','cerrado','20:19:44','2026-03-28','2026-03-29 02:19:44'),
(55,2,'2026-03-28','20:20:16','cerrado','20:24:39','2026-03-28','2026-03-29 02:24:39'),
(56,2,'2026-03-28','20:24:47','cerrado','12:27:26','2026-03-29','2026-03-29 18:27:26'),
(57,2,'2026-03-29','12:27:30','activo',NULL,NULL,'2026-03-29 18:27:30');
/*!40000 ALTER TABLE `turnos` ENABLE KEYS */;
UNLOCK TABLES;
commit;

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
  PRIMARY KEY (`id`),
  UNIQUE KEY `usuarios_unique` (`codigo`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `usuarios` VALUES
(2,0,'Administrador','$2b$12$m7tkAn0R7YnOzTQwORnBOet4j1RPIGdYayyhqOu/NBCs8dIAqHATm',0.00,'{\"admin\":true,\"encargado\":true}','string','2026-03-20 16:36:21'),
(3,2,'vic','$2b$12$K/ny9kdpYex1NqbT16X93uoTf1s/9wYudtEMbrindG48PecJVClYe',0.00,'{\"admin\":false,\"encargado\":true}','string','2026-03-20 16:36:21'),
(10,1,'Encargado','$2b$12$DEUK7oHLwy4lr7dCqxrdweyOotAZ3WYRqsFTQCznUYEd.jZKmqtEG',0.00,'{\"admin\":false,\"encargado\":true}','Solo encargado','2026-03-20 16:36:21'),
(11,3,'Sin acceso','$2b$12$lP4RrGPi9ElhpPPolUj8u.GNeeTHII04AAZD4br5x1Y4nAZkCMB5m',0.00,'{\"admin\":false,\"encargado\":false}','Sin acceso','2026-03-20 16:36:21');
/*!40000 ALTER TABLE `usuarios` ENABLE KEYS */;
UNLOCK TABLES;
commit;

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

-- Dump completed on 2026-03-29 12:48:53
