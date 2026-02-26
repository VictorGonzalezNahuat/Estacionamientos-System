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
  PRIMARY KEY (`id`),
  UNIQUE KEY `estado_estacionamiento_unique` (`placa`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `current_estacionamiento`
--

LOCK TABLES `current_estacionamiento` WRITE;
/*!40000 ALTER TABLE `current_estacionamiento` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `current_estacionamiento` VALUES
(29,'PRUEBA',1,2,36,'2026-02-23','17:03:11');
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
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `history_estacionamiento`
--

LOCK TABLES `history_estacionamiento` WRITE;
/*!40000 ALTER TABLE `history_estacionamiento` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `history_estacionamiento` VALUES
(1,1,2,11,'2026-02-14','19:12:59','2026-02-14','21:27:45','PLACA123',75.00),
(2,1,2,11,'2026-02-14','21:37:31','2026-02-14','21:39:49','PRUEBA',30.00),
(3,1,2,11,'2026-02-14','22:43:07','2026-02-14','22:44:07','PRUEBBB',30.00),
(4,1,2,12,'2026-02-15','08:03:49','2026-02-15','08:06:03','UNO',30.00),
(5,1,2,12,'2026-02-15','08:05:14','2026-02-15','15:01:36','dos',210.00),
(6,1,2,12,'2026-02-15','08:05:45','2026-02-15','15:01:42','TRES',210.00),
(7,1,2,27,'2026-02-17','19:05:11','2026-02-17','20:33:13','PRUEBA',45.00),
(8,1,2,27,'2026-02-17','19:52:15','2026-02-17','20:33:20','PRUEBA2',30.00),
(9,1,2,27,'2026-02-17','20:44:48','2026-02-18','14:08:26','PRUEBITA',465.00),
(10,1,2,27,'2026-02-18','14:08:32','2026-02-18','14:09:33','PRUEBITA',30.00),
(11,1,2,27,'2026-02-18','14:00:15','2026-02-18','14:11:15','ALERTA',30.00),
(12,1,2,27,'2026-02-17','21:07:30','2026-02-18','14:11:21','PRUEBA4',465.00),
(13,1,2,27,'2026-02-17','21:07:24','2026-02-18','14:11:26','PRUEBA2',465.00),
(14,1,2,27,'2026-02-17','21:07:06','2026-02-18','14:20:19','PRUEBA1',465.00),
(15,1,2,27,'2026-02-17','21:07:11','2026-02-18','15:00:17','PRUEBA3',480.00),
(16,1,2,27,'2026-02-17','21:07:35','2026-02-18','15:00:47','PRUEBA6',480.00),
(17,1,2,29,'2026-02-20','16:43:58','2026-02-20','16:46:55','INGRESA',30.00),
(18,1,2,27,'2026-02-18','15:00:42','2026-02-20','22:09:41','PRUEBITA',525.00),
(19,1,2,31,'2026-02-21','12:06:42','2026-02-21','12:07:48','PRUEBA',30.00),
(20,1,2,27,'2026-02-20','14:45:09','2026-02-21','12:07:54','PRUEBA2',585.00),
(21,1,2,31,'2026-02-21','12:06:47','2026-02-21','12:07:58','PRUEBA3',30.00),
(22,1,2,31,'2026-02-21','12:06:53','2026-02-21','12:08:03','PRUEBA4',30.00),
(23,1,2,31,'2026-02-21','12:06:57','2026-02-21','12:08:07','PRUEBA5',30.00),
(24,1,2,32,'2026-02-21','23:39:00','2026-02-21','23:40:00','ZAK555F',30.00),
(25,1,2,33,'2026-02-21','23:40:39','2026-02-21','23:41:39','ZAK555F',30.00),
(26,1,2,34,'2026-02-21','23:47:01','2026-02-21','23:48:21','PRUEBITA',30.00),
(27,1,2,34,'2026-02-21','23:47:37','2026-02-23','16:44:48','PRUEBITA2',600.00),
(28,1,2,35,'2026-02-23','16:45:39','2026-02-23','16:58:14','PRUEBA',30.00);
/*!40000 ALTER TABLE `history_estacionamiento` ENABLE KEYS */;
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
(1,35,1,35);
/*!40000 ALTER TABLE `state_estacionamiento` ENABLE KEYS */;
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
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tarifas`
--

LOCK TABLES `tarifas` WRITE;
/*!40000 ALTER TABLE `tarifas` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `tarifas` VALUES
(1,1,'carro',30.00,15.00,300.00,150.00,'observaedit',0,1);
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
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=37 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `turnos`
--

LOCK TABLES `turnos` WRITE;
/*!40000 ALTER TABLE `turnos` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `turnos` VALUES
(6,1,'2026-02-14','10:44:52','cerrado','10:45:15',NULL),
(7,1,'2026-02-14','10:47:50','cerrado','10:48:07',NULL),
(8,2,'2026-02-14','11:28:35','cerrado','11:42:43',NULL),
(9,2,'2026-02-14','11:44:38','cerrado','11:44:51',NULL),
(10,2,'2026-02-14','12:04:28','cerrado','12:06:02',NULL),
(11,2,'2026-02-14','19:12:52','cerrado','22:44:15',NULL),
(12,2,'2026-02-15','08:03:37','cerrado','15:01:56','2026-02-15'),
(13,2,'2026-02-16','18:59:29','cerrado','19:04:33','2026-02-16'),
(14,2,'2026-02-16','19:04:44','cerrado','19:06:23','2026-02-16'),
(15,2,'2026-02-16','19:06:29','cerrado','19:07:22','2026-02-16'),
(16,2,'2026-02-16','19:07:33','cerrado','19:10:13','2026-02-16'),
(17,2,'2026-02-16','19:10:17','cerrado','19:11:24','2026-02-16'),
(18,2,'2026-02-16','19:11:32','cerrado','19:11:41','2026-02-16'),
(19,2,'2026-02-16','19:12:03','cerrado','20:03:01','2026-02-16'),
(20,2,'2026-02-16','20:03:17','cerrado','20:05:51','2026-02-16'),
(21,2,'2026-02-16','20:07:52','cerrado','20:49:43','2026-02-16'),
(22,2,'2026-02-17','10:48:22','cerrado','10:49:25','2026-02-17'),
(23,2,'2026-02-17','11:06:50','cerrado','14:15:30','2026-02-17'),
(24,2,'2026-02-17','14:16:06','cerrado','17:17:56','2026-02-17'),
(25,2,'2026-02-17','17:19:44','cerrado','17:59:31','2026-02-17'),
(26,2,'2026-02-17','18:20:27','cerrado','18:20:56','2026-02-17'),
(27,2,'2026-02-17','19:04:22','cerrado','14:45:20','2026-02-20'),
(28,2,'2026-02-20','14:46:25','cerrado','14:49:55','2026-02-20'),
(29,2,'2026-02-20','14:53:08','cerrado','20:52:50','2026-02-20'),
(30,2,'2026-02-20','20:53:32','cerrado','09:36:23','2026-02-21'),
(31,2,'2026-02-21','12:06:36','cerrado','12:08:22','2026-02-21'),
(32,2,'2026-02-21','23:38:45','cerrado','23:40:11','2026-02-21'),
(33,2,'2026-02-21','23:40:34','cerrado','23:41:55','2026-02-21'),
(34,2,'2026-02-21','23:46:54','cerrado','23:48:33','2026-02-21'),
(35,2,'2026-02-23','16:44:39','cerrado','16:55:36','2026-02-23'),
(36,2,'2026-02-23','16:58:09','activo',NULL,NULL);
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
  PRIMARY KEY (`id`),
  UNIQUE KEY `usuarios_unique` (`codigo`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `usuarios`
--

LOCK TABLES `usuarios` WRITE;
/*!40000 ALTER TABLE `usuarios` DISABLE KEYS */;
set autocommit=0;
INSERT INTO `usuarios` VALUES
(1,1,'Victor','$2b$12$zh.6cz3lRRGHbf7MP6FVX.aat.br/ipVmeAy8bBYGpEPJ9jftnhSK',2.00,'{\"admin\": true}','ninguna'),
(2,0,'prueba','$2b$12$m7tkAn0R7YnOzTQwORnBOet4j1RPIGdYayyhqOu/NBCs8dIAqHATm',0.00,'{\"admin\": true}','string'),
(3,2,'vic','$2b$12$K/ny9kdpYex1NqbT16X93uoTf1s/9wYudtEMbrindG48PecJVClYe',0.00,'{\"admin\": true}','string');
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

-- Dump completed on 2026-02-26 16:15:46
