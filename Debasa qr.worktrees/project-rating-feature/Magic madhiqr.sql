CREATE DATABASE  IF NOT EXISTS `hotelqr` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `hotelqr`;
-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: hotelqr
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `menu`
--

DROP TABLE IF EXISTS `menu`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `menu` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `price` decimal(10,2) NOT NULL,
  `category` varchar(50) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `image` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=228 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `menu`
--

LOCK TABLES `menu` WRITE;
/*!40000 ALTER TABLE `menu` DISABLE KEYS */;
INSERT INTO `menu` VALUES (92,'Butternut Soup',450.00,'Soups','Fresh butternut soup','butternut_soup.jpg'),(93,'Potato & Leeks Soup',450.00,'Soups','Creamy potato and leeks soup','potato_leeks_soup.jpg'),(94,'Carrot & Ginger Soup',450.00,'Soups','Carrot soup blended with ginger','carrot_ginger_soup.jpg'),(95,'Broccoli / Cauliflower Cream Soup',450.00,'Soups','Creamy broccoli and cauliflower soup','broccoli_cauliflower_soup.jpg'),(96,'Mushroom Soup',450.00,'Soups','Fresh creamy mushroom soup','mushroom_soup.jpg'),(97,'Seafood Burida Soup',450.00,'Soups','Seafood Burida soup','seafood_burida_soup.jpg'),(98,'Hungarian Beef Soup',450.00,'Soups','Traditional Hungarian beef soup','hungarian_beef_soup.jpg'),(99,'English Breakfast',950.00,'Classic Breakfast','2 eggs, sausage, beef bacon, baked beans, tomatoes and toasted bread','english_breakfast.jpg'),(100,'Continental Breakfast',850.00,'Classic Breakfast','2 eggs, fresh salad and toasted bread','continental_breakfast.jpg'),(101,'Eggs Benedict',650.00,'Classic Breakfast','Poached eggs, beef bacon and avocado slices','eggs_benedict.jpg'),(102,'Shakshuka',500.00,'Classic Breakfast','Poached eggs in dania sauce','shakshuka.jpg'),(103,'Pan Fried Liver (Goat or Camel)',700.00,'Classic Breakfast','Fried liver with peppers served with Anjera, Chapati or Naan bread','pan_fried_liver.jpg'),(104,'Pancakes & Waffles',550.00,'Classic Breakfast','Served with fruits or ice cream','pancakes_waffles.jpg'),(105,'Florentine Breakfast',600.00,'Classic Breakfast','2 eggs, spinach and toasted bread','florentine_breakfast.jpg'),(106,'Avocado Toast',500.00,'Classic Breakfast','Avocado slices with eggs','avocado_toast.jpg'),(107,'French Toast',550.00,'Classic Breakfast','French toasted bread','french_toast.jpg'),(108,'Magic Breakfast Combo',1200.00,'Classic Breakfast','Sausage, beef bacon, liver skewers, spinach, 2 eggs, mushrooms and baked beans','magic_breakfast_combo.jpg'),(109,'Greek Salad',750.00,'Salads','Bell pepper, olives, feta cheese, onions, French dressing','greek_salad.jpg'),(110,'Garden Salad',500.00,'Salads','Soft and hard lettuce, carrot strips, onions, cucumber dressed with apple cider vinegar','garden_salad.jpg'),(111,'M&M Salad',750.00,'Salads','Soft lettuce mixed with quinoa seeds and beetroot','mm_salad.jpg'),(112,'Texas Salad',850.00,'Salads','Soft and hard lettuce mixed with French dressing topped with sauce','texas_salad.jpg'),(113,'Tuna Salad',750.00,'Salads','Fresh tuna salad','tuna_salad.jpg'),(114,'Mutton Mandi',800.00,'Magic Mandi Corner','1 portion of goat served with Mandi rice, salad and appetizers','mutton_mandi.jpg'),(115,'Chicken Mandi',600.00,'Magic Mandi Corner','1 portion of chicken served with Mandi rice, salad and appetizers','chicken_mandi.jpg'),(116,'Fish Mandi',800.00,'Magic Mandi Corner','1 portion of fried fish served with Mandi rice, salad and appetizers','fish_mandi.jpg'),(117,'Magic Mandi Half Goat',7000.00,'Magic Mandi Corner','Half goat platter served with Mandi rice, salad and appetizers','half_goat_mandi.jpg'),(118,'Magic Mandi Full Goat',14000.00,'Magic Mandi Corner','Full goat platter served with Mandi rice, salad and appetizers','full_goat_mandi.jpg'),(119,'Carbonara Tagliatelle',850.00,'Pasta','Tagliatelle pasta with beef bacon, eggs and cream','carbonara_tagliatelle.jpg'),(120,'Chicken Alfredo',750.00,'Pasta','Penne pasta tossed with chicken in creamy sauce with mushroom topping','chicken_alfredo.jpg'),(121,'Seafood Pasta',1100.00,'Pasta','Prawns and calamari cooked with garlic in dania sauce with linguini pasta','seafood_pasta.jpg'),(122,'Spaghetti Bolognese',800.00,'Pasta','Italian bolognese topped with cheese','spaghetti_bolognese.jpg'),(123,'Penne Arrabbiata',700.00,'Pasta','Penne pasta with mixed vegetables in spicy garlic tomato sauce topped with cheese','penne_arrabbiata.jpg'),(124,'Linguini Dania',650.00,'Pasta','Linguini pasta in red sauce','linguini_dania.jpg'),(125,'Shrimp Pasta',900.00,'Pasta','Spaghetti pasta with prawns in olive oil and garlic','shrimp_pasta.jpg'),(126,'Penne Primavera',800.00,'Pasta','Penne pasta with fresh vegetables','penne_primavera.jpg'),(127,'Chicken Breast',350.00,'Grill Point','Grilled chicken breast','chicken_breast.jpg'),(128,'Chicken Leg',300.00,'Grill Point','Grilled chicken leg','chicken_leg.jpg'),(129,'Mkate Mayai',300.00,'Grill Point','Fresh Mkate Mayai','mkate_mayai.jpg'),(130,'Mishkaki',400.00,'Grill Point','Grilled beef skewers','mishkaki.jpg'),(131,'Beef Shawarma',400.00,'Grill Point','Beef shawarma wrap','beef_shawarma.jpg'),(132,'Chicken Shawarma',300.00,'Grill Point','Chicken shawarma wrap','chicken_shawarma.jpg'),(133,'Shish Kabab',500.00,'Grill Point','Grilled shish kabab','shish_kabab.jpg'),(134,'Chips',300.00,'Grill Point','French fries','chips.jpg'),(135,'Whole Fish with Grams',1200.00,'Grill Point','Whole fish served with grams','whole_fish_grams.jpg'),(136,'Malaysian Chicken Curry',1000.00,'Curries','Creamy chicken curry served with rice, naan bread or chapati','malaysian_chicken_curry.jpg'),(137,'Prawns Curry',1300.00,'Curries','Special prawns curry served with your choice of rice, naan bread or chapati','prawns_curry.jpg'),(138,'Veggie Curry',750.00,'Curries','Well prepared vegetable curry served with your choice of bread','veggie_curry.jpg'),(139,'Chicken Tikka Masala',800.00,'Curries','Chicken tikka cooked in rich masala sauce','chicken_tikka_masala.jpg'),(140,'Chicken Deluxe Pizza',900.00,'Pizza','Chicken cubes marinated in green curry topped on pizza','chicken_deluxe_pizza.jpg'),(141,'Margherita',700.00,'Pizza','Classic Italian pizza with mozzarella, pomodoro and basil','margherita.jpg'),(142,'Beef Pizza',900.00,'Pizza','Pomodoro, mozzarella, marinated beef strips and chives','beef_pizza.jpg'),(143,'Magic Mandi Special Pizza',900.00,'Pizza','Minced meat, cheese, mushrooms, peppers and strawberry','magic_mandi_special_pizza.jpg'),(144,'Pizza Funghi',850.00,'Pizza','Mushrooms, sliced onions and sweet corn','pizza_funghi.jpg'),(145,'Beef Burger',700.00,'Fries & Burgers','Beef patty, salad, tomato and gherkins','beef_burger.jpg'),(146,'Egg Cheese Burger',850.00,'Fries & Burgers','Beef patty, egg, cheese and salad','egg_cheese_burger.jpg'),(147,'Cheese Burger',600.00,'Fries & Burgers','Beef patty, cheese and salad','cheese_burger.jpg'),(148,'Chicken Burger',650.00,'Fries & Burgers','Chicken patty with cheese and salad','chicken_burger.jpg'),(149,'M&M Burger Combo',1200.00,'Fries & Burgers','Chicken, salad, gherkins and aioli','mm_burger_combo.jpg'),(150,'Plain Chips',300.00,'Fries & Burgers','Crispy plain French fries','plain_chips.jpg'),(151,'Masala Chips',350.00,'Fries & Burgers','French fries tossed in masala seasoning','masala_chips.jpg'),(152,'Garlic Chips',350.00,'Fries & Burgers','French fries with garlic seasoning','garlic_chips.jpg'),(153,'Mashed Potatoes',400.00,'Fries & Burgers','Creamy mashed potatoes','mashed_potatoes.jpg'),(154,'Single Espresso',240.00,'Hot Drinks','Single shot espresso','single_espresso.jpg'),(155,'Double Espresso',300.00,'Hot Drinks','Double shot espresso','double_espresso.jpg'),(156,'Single Cappuccino',300.00,'Hot Drinks','Single cappuccino','single_cappuccino.jpg'),(157,'Double Cappuccino',350.00,'Hot Drinks','Double cappuccino','double_cappuccino.jpg'),(158,'Single Latte',300.00,'Hot Drinks','Single latte','single_latte.jpg'),(159,'Double Latte',350.00,'Hot Drinks','Double latte','double_latte.jpg'),(160,'Flat White',300.00,'Hot Drinks','Flat white coffee','flat_white.jpg'),(161,'Americano',300.00,'Hot Drinks','Fresh americano coffee','americano.jpg'),(162,'Single Latte Macchiato',250.00,'Hot Drinks','Single latte macchiato','single_latte_macchiato.jpg'),(163,'Double Latte Macchiato',300.00,'Hot Drinks','Double latte macchiato','double_latte_macchiato.jpg'),(164,'Filter Coffee',370.00,'Hot Drinks','Fresh filter coffee','filter_coffee.jpg'),(165,'Hot Chocolate',340.00,'Hot Drinks','Rich hot chocolate','hot_chocolate.jpg'),(166,'Kenyan Black Tea',150.00,'Hot Drinks','Traditional Kenyan black tea','kenyan_black_tea.jpg'),(167,'Kenyan Milk Tea',180.00,'Hot Drinks','Traditional Kenyan milk tea','kenyan_milk_tea.jpg'),(168,'Camel Milk Tea',200.00,'Hot Drinks','Tea prepared with camel milk','camel_milk_tea.jpg'),(169,'Herbs Tea',260.00,'Hot Drinks','Fresh herbal tea','herbs_tea.jpg'),(170,'Chai Latte',350.00,'Hot Drinks','Creamy chai latte','chai_latte.jpg'),(171,'Vanilla Milkshake',500.00,'Milkshakes','Creamy vanilla milkshake','vanilla_milkshake.jpg'),(172,'Chocolate Milkshake',500.00,'Milkshakes','Rich chocolate milkshake','chocolate_milkshake.jpg'),(173,'Strawberry Milkshake',500.00,'Milkshakes','Fresh strawberry milkshake','strawberry_milkshake.jpg'),(174,'Oreo Milkshake',550.00,'Milkshakes','Oreo cookies blended with ice cream','oreo_milkshake.jpg'),(175,'Mango Milkshake',550.00,'Milkshakes','Fresh mango blended with milk and ice cream','mango_milkshake.jpg'),(176,'Banana Milkshake',500.00,'Milkshakes','Fresh banana blended with milk and ice cream','banana_milkshake.jpg'),(177,'Dates Milkshake',600.00,'Milkshakes','Dates blended with fresh milk and ice cream','dates_milkshake.jpg'),(178,'Avocado Milkshake',600.00,'Milkshakes','Fresh avocado blended with milk and ice cream','avocado_milkshake.jpg'),(179,'Mango Smoothie',500.00,'Smoothies','Fresh mango blended with yogurt and ice','mango_smoothie.jpg'),(180,'Strawberry Smoothie',500.00,'Smoothies','Fresh strawberries blended with yogurt','strawberry_smoothie.jpg'),(181,'Passion Smoothie',500.00,'Smoothies','Fresh passion fruit blended with yogurt','passion_smoothie.jpg'),(182,'Banana Smoothie',500.00,'Smoothies','Fresh banana blended with yogurt','banana_smoothie.jpg'),(183,'Pineapple Smoothie',500.00,'Smoothies','Fresh pineapple blended with yogurt','pineapple_smoothie.jpg'),(184,'Avocado Smoothie',550.00,'Smoothies','Fresh avocado blended with yogurt','avocado_smoothie.jpg'),(185,'Mixed Fruit Smoothie',600.00,'Smoothies','A blend of seasonal fresh fruits with yogurt','mixed_fruit_smoothie.jpg'),(186,'Watermelon Juice',300.00,'Fresh Juice','Fresh watermelon juice','watermelon_juice.jpg'),(187,'Guava Juice',300.00,'Fresh Juice','Fresh guava juice','guava_juice.jpg'),(188,'Coconut Juice',300.00,'Fresh Juice','Fresh coconut juice','coconut_juice.jpg'),(189,'Mango Juice',300.00,'Fresh Juice','Fresh mango juice','mango_juice.jpg'),(190,'Carrot Juice',300.00,'Fresh Juice','Fresh carrot juice','carrot_juice.jpg'),(191,'Orange Juice',300.00,'Fresh Juice','Fresh orange juice','orange_juice.jpg'),(192,'Passion Juice',300.00,'Fresh Juice','Fresh passion fruit juice','passion_juice.jpg'),(193,'Spandes Juice',300.00,'Fresh Juice','Fresh spandes juice','spandes_juice.jpg'),(194,'Pineapple Juice',300.00,'Fresh Juice','Fresh pineapple juice','pineapple_juice.jpg'),(195,'Khungu (Bedaan) Juice',300.00,'Fresh Juice','Fresh khungu (bedaan) juice','khungu_bedaan_juice.jpg'),(196,'Sweet Melon Juice',300.00,'Fresh Juice','Fresh sweet melon juice','sweet_melon_juice.jpg'),(197,'Beetroot Juice',300.00,'Fresh Juice','Fresh beetroot juice','beetroot_juice.jpg'),(198,'Apple Juice',300.00,'Fresh Juice','Fresh apple juice','apple_juice.jpg'),(199,'Tropical Juice',300.00,'Fresh Juice','Fresh tropical fruit juice','tropical_juice.jpg'),(200,'Papaya Juice',300.00,'Fresh Juice','Fresh papaya juice','papaya_juice.jpg'),(201,'Avocado Juice',300.00,'Fresh Juice','Fresh avocado juice','avocado_juice.jpg'),(202,'Vimto Juice',300.00,'Fresh Juice','Fresh Vimto juice','vimto_juice.jpg'),(203,'Classic Lemonade',350.00,'Lemonades','Fresh homemade lemonade','classic_lemonade.jpg'),(204,'Mint Lemonade',400.00,'Lemonades','Fresh lemonade with mint','mint_lemonade.jpg'),(205,'Blue Lemonade',400.00,'Lemonades','Blue flavored lemonade','blue_lemonade.jpg'),(206,'Strawberry Lemonade',450.00,'Lemonades','Fresh strawberry lemonade','strawberry_lemonade.jpg'),(207,'Passion Lemonade',450.00,'Lemonades','Passion fruit lemonade','passion_lemonade.jpg'),(208,'Mango Lemonade',450.00,'Lemonades','Fresh mango lemonade','mango_lemonade.jpg'),(209,'Classic Mojito',450.00,'Mojitos','Refreshing classic mojito','classic_mojito.jpg'),(210,'Blue Mojito',500.00,'Mojitos','Refreshing blue mojito','blue_mojito.jpg'),(211,'Passion Mojito',500.00,'Mojitos','Refreshing passion fruit mojito','passion_mojito.jpg'),(212,'Strawberry Mojito',500.00,'Mojitos','Refreshing strawberry mojito','strawberry_mojito.jpg'),(213,'Mango Mojito',500.00,'Mojitos','Refreshing mango mojito','mango_mojito.jpg'),(214,'Watermelon Mojito',500.00,'Mojitos','Refreshing watermelon mojito','watermelon_mojito.jpg'),(215,'Green Apple Mojito',500.00,'Mojitos','Refreshing green apple mojito','green_apple_mojito.jpg'),(216,'Kids Chicken Nuggets & Fries',650.00,'Kids Special Menu','Chicken nuggets served with fries','kids_nuggets_fries.jpg'),(217,'Kids Chicken Burger & Fries',700.00,'Kids Special Menu','Mini chicken burger served with fries','kids_chicken_burger.jpg'),(218,'Kids Beef Burger & Fries',700.00,'Kids Special Menu','Mini beef burger served with fries','kids_beef_burger.jpg'),(219,'Kids Chicken Fingers & Fries',700.00,'Kids Special Menu','Crispy chicken fingers served with fries','kids_chicken_fingers.jpg'),(220,'Kids Mini Pizza',750.00,'Kids Special Menu','Mini pizza for kids','kids_mini_pizza.jpg'),(221,'Kids Pasta',650.00,'Kids Special Menu','Creamy pasta for kids','kids_pasta.jpg'),(227,'Chips Shawarma',550.00,'Grill Point','chicken shawarma served with crispy chips.','chips_shawarma.jpg');
/*!40000 ALTER TABLE `menu` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_items`
--

DROP TABLE IF EXISTS `order_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_items` (
  `id` int NOT NULL AUTO_INCREMENT,
  `order_id` int DEFAULT NULL,
  `menu_name` varchar(100) DEFAULT NULL,
  `quantity` int DEFAULT NULL,
  `price` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `order_id` (`order_id`),
  CONSTRAINT `order_items_ibfk_1` FOREIGN KEY (`order_id`) REFERENCES `orders` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=81 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_items`
--

LOCK TABLES `order_items` WRITE;
/*!40000 ALTER TABLE `order_items` DISABLE KEYS */;
INSERT INTO `order_items` VALUES (2,1,'Pizza',1,950.00),(3,2,'Soda',1,150.00),(4,2,'Pizza',1,950.00),(6,3,'Soda',1,150.00),(8,5,'chapati',3,60.00),(9,5,'chicken biryani',2,970.00),(10,6,'Soda',1,150.00),(14,7,'chapati',1,60.00),(15,7,'chicken biryani',1,970.00),(16,8,'shawarma',1,350.00),(17,8,'Mandi Chicken',1,820.00),(18,9,'shawarma',1,350.00),(19,9,'chapati',1,60.00),(20,9,'Pizza',1,950.00),(21,9,'Soda',1,150.00),(22,9,'chicken biryani',1,970.00),(23,10,'Pizza',1,950.00),(24,10,'Soda',1,150.00),(25,10,'shawarma',1,350.00),(26,11,'Pizza',1,950.00),(27,11,'shawarma',1,350.00),(28,11,'Mandi Chicken',1,820.00),(29,12,'Soda',1,150.00),(30,12,'chicken biryani',1,970.00),(31,12,'shawarma',1,350.00),(32,12,'Mandi Chicken',1,820.00),(33,13,'shawarma',1,350.00),(34,13,'Mandi Chicken',1,820.00),(35,13,'chicken biryani',1,970.00),(36,13,'Pilau Chicken',1,690.00),(37,14,'shawarma',1,350.00),(38,14,'chapati',1,60.00),(39,14,'Pilau Chicken',1,690.00),(40,14,'Pilau Fish',1,690.00),(41,15,'Soda',1,150.00),(42,15,'chicken biryani',1,970.00),(43,15,'shawarma',1,350.00),(44,15,'Mandi Chicken',1,820.00),(45,16,'Pilau Fish',1,690.00),(46,16,'chicken biryani',1,970.00),(47,16,'Mandi Chicken',1,820.00),(48,16,'Pilau Chicken',1,690.00),(49,16,'Pilau mutton',1,690.00),(50,17,'Pizza',1,950.00),(51,17,'chicken biryani',1,970.00),(52,18,'Pizza',1,950.00),(53,18,'Soda',1,150.00),(54,18,'chicken biryani',1,970.00),(55,19,'Mandi Chicken',1,820.00),(56,19,'shawarma',1,350.00),(57,20,'Mandi Chicken',1,820.00),(58,20,'Soda',2,150.00),(59,20,'shawarma',2,350.00),(60,21,'Mandi Chicken',1,820.00),(61,21,'Pilau mutton',1,690.00),(62,22,'Soda',1,150.00),(63,22,'chicken biryani',1,970.00),(64,22,'Pizza',1,950.00),(65,22,'shawarma',1,350.00),(66,23,'English Breakfast',1,850.00),(67,23,'Spanish Omelette',1,650.00),(68,23,'Pancakes',1,500.00),(69,24,'Potato & Leeks Soup',2,450.00),(70,25,'Potato & Leeks Soup',1,450.00),(71,25,'Carrot & Ginger Soup',1,450.00),(72,25,'Chicken Mandi',1,600.00),(73,25,'Fish Mandi',1,800.00),(74,26,'English Breakfast',1,950.00),(75,26,'Guava Juice',1,300.00),(76,27,'Potato & Leeks Soup',1,450.00),(77,27,'Carrot & Ginger Soup',1,450.00),(78,28,'Potato & Leeks Soup',1,450.00),(79,28,'Carrot & Ginger Soup',1,450.00),(80,29,'Mashed Potatoes',1,400.00);
/*!40000 ALTER TABLE `order_items` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `orders`
--

DROP TABLE IF EXISTS `orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orders` (
  `id` int NOT NULL AUTO_INCREMENT,
  `customer_name` varchar(100) DEFAULT NULL,
  `table_number` int DEFAULT NULL,
  `total` decimal(10,2) DEFAULT NULL,
  `status` varchar(20) DEFAULT 'Pending',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `waiter_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_orders_waiter` (`waiter_id`),
  CONSTRAINT `fk_orders_waiter` FOREIGN KEY (`waiter_id`) REFERENCES `waiters` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `orders`
--

LOCK TABLES `orders` WRITE;
/*!40000 ALTER TABLE `orders` DISABLE KEYS */;
INSERT INTO `orders` VALUES (1,'michael',2,1600.00,'Completed','2026-07-30 19:53:41',NULL),(2,'john',6,1100.00,'Completed','2026-07-30 20:56:47',NULL),(3,'nhfhfhhf',3,800.00,'Completed','2026-07-30 21:09:26',NULL),(4,'eeee',1,650.00,'Completed','2026-07-30 21:09:47',NULL),(5,'mike',2,2120.00,'Completed','2026-07-30 21:48:30',NULL),(6,'joseph',4,1150.00,'Completed','2026-07-30 21:58:13',NULL),(7,'mulkam',1,1380.00,'Preparing','2026-07-31 05:38:01',NULL),(8,'Guest',5,1170.00,'Pending','2026-07-31 09:37:41',NULL),(9,'Guest',1,2480.00,'Completed','2026-07-31 11:07:12',1),(10,'Guest',4,1450.00,'Pending','2026-07-31 11:14:46',1),(11,'Guest',5,2120.00,'Pending','2026-07-31 11:27:34',1),(12,'Guest',5,2290.00,'Completed','2026-07-31 11:29:58',1),(13,'Guest',5,2830.00,'Completed','2026-07-31 11:54:32',1),(14,'Guest',1,1790.00,'Completed','2026-07-31 12:01:31',1),(15,'Guest',50,2290.00,'Completed','2026-07-31 17:15:14',5),(16,'Customer',15,3860.00,'Pending','2026-07-31 19:06:48',NULL),(17,'Guest',1,1920.00,'Completed','2026-07-31 21:06:18',NULL),(18,'Guest',1,2070.00,'Pending','2026-07-31 21:49:03',1),(19,'Guest',5,1170.00,'Completed','2026-07-31 23:00:20',1),(20,'Guest',4,1820.00,'Completed','2026-07-31 23:13:02',1),(21,'Guest',16,1510.00,'Pending','2026-08-01 09:33:54',2),(22,'Guest',5,2420.00,'Completed','2026-08-01 10:00:26',1),(23,'Guest',50,2000.00,'Pending','2026-08-01 13:33:15',5),(24,'Guest',5,900.00,'Completed','2026-08-01 13:49:39',1),(25,'Guest',50,2300.00,'Completed','2026-08-01 21:11:42',5),(26,'Guest',50,1250.00,'Completed','2026-08-02 18:53:32',5),(27,'Guest',36,900.00,'Completed','2026-08-02 18:58:06',4),(28,'Guest',36,900.00,'Pending','2026-08-02 19:22:21',4),(29,'Guest',49,400.00,'Pending','2026-08-03 06:35:46',5);
/*!40000 ALTER TABLE `orders` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `table_assignments`
--

DROP TABLE IF EXISTS `table_assignments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `table_assignments` (
  `table_number` int NOT NULL,
  `waiter_id` int NOT NULL,
  PRIMARY KEY (`table_number`),
  KEY `waiter_id` (`waiter_id`),
  CONSTRAINT `table_assignments_ibfk_1` FOREIGN KEY (`waiter_id`) REFERENCES `waiters` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `table_assignments`
--

LOCK TABLES `table_assignments` WRITE;
/*!40000 ALTER TABLE `table_assignments` DISABLE KEYS */;
INSERT INTO `table_assignments` VALUES (1,1),(2,1),(3,1),(4,1),(5,1),(6,1),(7,1),(8,1),(9,1),(10,1),(11,2),(12,2),(13,2),(14,2),(15,2),(16,2),(17,2),(18,2),(19,2),(20,2),(21,3),(22,3),(23,3),(24,3),(25,3),(26,3),(27,3),(28,3),(29,3),(30,3),(31,4),(32,4),(33,4),(34,4),(35,4),(36,4),(37,4),(38,4),(39,4),(40,4),(41,5),(42,5),(43,5),(44,5),(45,5),(46,5),(47,5),(48,5),(49,5),(50,5);
/*!40000 ALTER TABLE `table_assignments` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `waiters`
--

DROP TABLE IF EXISTS `waiters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `waiters` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `status` varchar(20) DEFAULT 'Active',
  `table_number` int DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `waiters`
--

LOCK TABLES `waiters` WRITE;
/*!40000 ALTER TABLE `waiters` DISABLE KEYS */;
INSERT INTO `waiters` VALUES (1,'Michael','0700000001','Active',NULL),(2,'Grace','0700000002','Active',NULL),(3,'Brian','0700000003','Active',NULL),(4,'Mercy','0700000004','Active',NULL),(5,'John','0700000005','Active',NULL);
/*!40000 ALTER TABLE `waiters` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-04 16:49:21
