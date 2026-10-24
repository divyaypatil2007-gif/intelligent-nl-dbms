-- =====================================================================
-- Inventory Management Database Schema & Seed Data
-- For Intelligent Natural Language Database Query System (NL-DBMS)
-- =====================================================================

CREATE DATABASE IF NOT EXISTS `inventory_management`;
USE `inventory_management`;

-- Drop existing tables if needed (in reverse dependency order)
DROP TABLE IF EXISTS `inventory`;
DROP TABLE IF EXISTS `supplier_order`;
DROP TABLE IF EXISTS `customer_order_details`;
DROP TABLE IF EXISTS `customer_order`;
DROP TABLE IF EXISTS `supplier`;
DROP TABLE IF EXISTS `warehouse`;
DROP TABLE IF EXISTS `products`;
DROP TABLE IF EXISTS `category`;

-- ---------------------------------------------------------------------
-- 1. Category Table
-- ---------------------------------------------------------------------
CREATE TABLE `category` (
    `Category_ID` INT AUTO_INCREMENT PRIMARY KEY,
    `Category_Name` VARCHAR(100) NOT NULL UNIQUE,
    `description` TEXT,
    `created_on` DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 2. Products Table
-- ---------------------------------------------------------------------
CREATE TABLE `products` (
    `Product_ID` INT AUTO_INCREMENT PRIMARY KEY,
    `Product_Name` VARCHAR(150) NOT NULL,
    `description` TEXT,
    `Category_ID` INT,
    `Cost_Price` DECIMAL(10, 2) NOT NULL,
    `Selling_Price` DECIMAL(10, 2) NOT NULL,
    `reorder_level` SMALLINT DEFAULT 10,
    `Unit` VARCHAR(20) DEFAULT 'piece',
    `weight` FLOAT,
    `Warranty_Months` TINYINT DEFAULT 12,
    `Manufacturing_Year` YEAR,
    `Is_Available` TINYINT DEFAULT 1,
    CONSTRAINT `fk_products_category`
        FOREIGN KEY (`Category_ID`) REFERENCES `category` (`Category_ID`)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 3. Customer Table
-- ---------------------------------------------------------------------
CREATE TABLE `customer` (
    `Customer_ID` INT AUTO_INCREMENT PRIMARY KEY,
    `Customer_Name` VARCHAR(100) NOT NULL,
    `phone` BIGINT UNIQUE,
    `Email` VARCHAR(100) UNIQUE,
    `address` TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 4. Customer Order Table
-- ---------------------------------------------------------------------
CREATE TABLE `customer_order` (
    `Order_ID` INT AUTO_INCREMENT PRIMARY KEY,
    `Customer_ID` INT,
    `Order_Date` DATE NOT NULL,
    `Total_Amount` DECIMAL(12, 2) DEFAULT 0.00,
    `payment_method` ENUM('Cash', 'UPI', 'Card', 'Net Banking') DEFAULT 'UPI',
    `Order_Status` ENUM('Pending', 'Packed', 'Shipped', 'Delivered', 'Cancelled') DEFAULT 'Pending',
    CONSTRAINT `fk_order_customer`
        FOREIGN KEY (`Customer_ID`) REFERENCES `customer` (`Customer_ID`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 5. Customer Order Details Table
-- Note: Does NOT have Customer_ID directly; traverses via customer_order
-- ---------------------------------------------------------------------
CREATE TABLE `customer_order_details` (
    `Order_detail_id` SMALLINT AUTO_INCREMENT PRIMARY KEY,
    `Order_ID` INT NOT NULL,
    `Product_ID` INT NOT NULL,
    `Quantity` SMALLINT NOT NULL DEFAULT 1,
    `Selling_Price` DECIMAL(10, 2) NOT NULL,
    `Subtotal` DECIMAL(12, 2) NOT NULL,
    CONSTRAINT `fk_order_details_order`
        FOREIGN KEY (`Order_ID`) REFERENCES `customer_order` (`Order_ID`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_order_details_product`
        FOREIGN KEY (`Product_ID`) REFERENCES `products` (`Product_ID`)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 6. Supplier Table
-- ---------------------------------------------------------------------
CREATE TABLE `supplier` (
    `Supplier_ID` INT AUTO_INCREMENT PRIMARY KEY,
    `Supplier_Name` VARCHAR(100) NOT NULL,
    `phone` BIGINT UNIQUE,
    `Email` VARCHAR(100) UNIQUE,
    `address` TEXT,
    `GST_NO` CHAR(15),
    `Contact_Person` VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 7. Warehouse Table
-- ---------------------------------------------------------------------
CREATE TABLE `warehouse` (
    `Warehouse_ID` INT AUTO_INCREMENT PRIMARY KEY,
    `Warehouse_Name` VARCHAR(100) NOT NULL,
    `Location` VARCHAR(100) NOT NULL,
    `Manager` VARCHAR(100),
    `Capacity` MEDIUMINT DEFAULT 1000
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 8. Supplier Order Table
-- ---------------------------------------------------------------------
CREATE TABLE `supplier_order` (
    `Supplier_order_id` SMALLINT AUTO_INCREMENT PRIMARY KEY,
    `Supplier_ID` INT NOT NULL,
    `Product_ID` INT NOT NULL,
    `Warehouse_ID` INT NOT NULL,
    `Quantity` SMALLINT NOT NULL,
    `Purchase_Price` DECIMAL(10, 2) NOT NULL,
    `Order_Date` DATE NOT NULL,
    `Delivery_Time` TIME,
    CONSTRAINT `fk_supplier_order_supplier`
        FOREIGN KEY (`Supplier_ID`) REFERENCES `supplier` (`Supplier_ID`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_supplier_order_product`
        FOREIGN KEY (`Product_ID`) REFERENCES `products` (`Product_ID`)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT `fk_supplier_order_warehouse`
        FOREIGN KEY (`Warehouse_ID`) REFERENCES `warehouse` (`Warehouse_ID`)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ---------------------------------------------------------------------
-- 9. Inventory Table
-- ---------------------------------------------------------------------
CREATE TABLE `inventory` (
    `Product_ID` INT NOT NULL,
    `Warehouse_ID` INT NOT NULL,
    `Quantity` MEDIUMINT NOT NULL DEFAULT 0,
    PRIMARY KEY (`Product_ID`, `Warehouse_ID`),
    CONSTRAINT `fk_inventory_product`
        FOREIGN KEY (`Product_ID`) REFERENCES `products` (`Product_ID`)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT `fk_inventory_warehouse`
        FOREIGN KEY (`Warehouse_ID`) REFERENCES `warehouse` (`Warehouse_ID`)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================================================================
-- Seed Data
-- =====================================================================

INSERT INTO `category` (`Category_ID`, `Category_Name`, `description`) VALUES
(1, 'Laptops', 'High performance and ultrabook laptops'),
(2, 'Smartphones', 'Mobile phones and accessories'),
(3, 'Audio', 'Headphones, earbuds, and speakers'),
(4, 'Storage', 'Internal & External SSDs and HDDs'),
(5, 'Monitors', 'Display screens and gaming monitors');

INSERT INTO `products` (`Product_ID`, `Product_Name`, `description`, `Category_ID`, `Cost_Price`, `Selling_Price`, `reorder_level`, `Unit`, `weight`, `Warranty_Months`, `Manufacturing_Year`, `Is_Available`) VALUES
(1, 'ThinkPad X1 Carbon', 'Intel Core i7 16GB 512GB SSD', 1, 85000.00, 115000.00, 5, 'piece', 1.1, 36, 2024, 1),
(2, 'MacBook Air M2', 'Apple M2 8-core CPU 8GB 256GB SSD', 1, 78000.00, 99900.00, 8, 'piece', 1.24, 12, 2023, 1),
(3, 'Dell XPS 13', 'Intel i7 13th Gen 16GB 1TB SSD', 1, 95000.00, 129000.00, 4, 'piece', 1.17, 24, 2024, 1),
(4, 'Galaxy S24 Ultra', 'Snapdragon 8 Gen 3 12GB 256GB Titanium', 2, 92000.00, 119999.00, 10, 'piece', 0.23, 12, 2024, 1),
(5, 'iPhone 15 Pro', 'A17 Pro 128GB Natural Titanium', 2, 98000.00, 124900.00, 6, 'piece', 0.18, 12, 2023, 1),
(6, 'Sony WH-1000XM5', 'Wireless Noise Cancelling Headphones', 3, 18000.00, 26990.00, 12, 'piece', 0.25, 12, 2023, 1),
(7, 'AirPods Pro 2', 'Active Noise Cancellation USB-C', 3, 16000.00, 21900.00, 15, 'piece', 0.05, 12, 2024, 1),
(8, 'Samsung 990 Pro 2TB', 'PCIe 4.0 NVMe M.2 Internal SSD', 4, 11000.00, 16499.00, 20, 'piece', 0.03, 60, 2024, 1),
(9, 'LG UltraGear 27"', 'QHD 165Hz IPS Gaming Monitor', 5, 17500.00, 23999.00, 7, 'piece', 6.0, 36, 2023, 1),
(10, 'Dell Ultrasharp 32"', '4K USB-C Hub Monitor', 5, 52000.00, 68000.00, 2, 'piece', 8.5, 36, 2024, 0);

INSERT INTO `customer` (`Customer_ID`, `Customer_Name`, `phone`, `Email`, `address`) VALUES
(1, 'Aarav Sharma', 9876543210, 'aarav.sharma@example.com', 'Flat 402, Green Valley, Pune'),
(2, 'Priya Patel', 9822334455, 'priya.patel@example.com', '12 Park Street, Mumbai'),
(3, 'Rohan Verma', 9898112233, 'rohan.verma@example.com', 'Sector 15, Noida'),
(4, 'Ananya Iyer', 9765432109, 'ananya.iyer@example.com', 'Indiranagar, Bangalore'),
(5, 'Vikram Malhotra', 9123456789, 'vikram.m@example.com', 'Banjara Hills, Hyderabad');

INSERT INTO `warehouse` (`Warehouse_ID`, `Warehouse_Name`, `Location`, `Manager`, `Capacity`) VALUES
(1, 'West Hub Pune', 'Pune', 'Suresh Jadhav', 5000),
(2, 'Mumbai Central Logistics', 'Mumbai', 'Sunil Mehta', 12000),
(3, 'North Depot Delhi', 'Delhi', 'Rajesh Gupta', 8000),
(4, 'South Hub Bengaluru', 'Bangalore', 'Ramesh Rao', 9000);

INSERT INTO `supplier` (`Supplier_ID`, `Supplier_Name`, `phone`, `Email`, `address`, `GST_NO`, `Contact_Person`) VALUES
(1, 'TechSource India Pvt Ltd', 9820011223, 'sales@techsource.in', 'Electronic City, Bangalore', '29AABCU9603R1ZM', 'Kunal Shah'),
(2, 'Global Components Mumbai', 9819922334, 'orders@globalcomp.com', 'Andheri East, Mumbai', '27AAECG4101P1Z5', 'Pradeep Kulkarni'),
(3, 'Apex Electronics Pune', 9860033445, 'contact@apexelectronics.in', 'Hinjewadi Phase 1, Pune', '27AACCA1234B1ZK', 'Mahesh Joshi');

INSERT INTO `customer_order` (`Order_ID`, `Customer_ID`, `Order_Date`, `Total_Amount`, `payment_method`, `Order_Status`) VALUES
(1, 1, '2024-09-10', 115000.00, 'UPI', 'Delivered'),
(2, 2, '2024-09-15', 26990.00, 'Card', 'Delivered'),
(3, 3, '2024-10-01', 124900.00, 'Net Banking', 'Shipped'),
(4, 1, '2024-10-05', 21900.00, 'UPI', 'Packed'),
(5, 4, '2024-10-12', 140999.00, 'UPI', 'Delivered'),
(6, 5, '2024-10-18', 32998.00, 'Cash', 'Pending');

INSERT INTO `customer_order_details` (`Order_detail_id`, `Order_ID`, `Product_ID`, `Quantity`, `Selling_Price`, `Subtotal`) VALUES
(1, 1, 1, 1, 115000.00, 115000.00),
(2, 2, 6, 1, 26990.00, 26990.00),
(3, 3, 5, 1, 124900.00, 124900.00),
(4, 4, 7, 1, 21900.00, 21900.00),
(5, 5, 4, 1, 119999.00, 119999.00),
(6, 5, 7, 1, 21000.00, 21000.00),
(7, 6, 8, 2, 16499.00, 32998.00);

INSERT INTO `supplier_order` (`Supplier_order_id`, `Supplier_ID`, `Product_ID`, `Warehouse_ID`, `Quantity`, `Purchase_Price`, `Order_Date`, `Delivery_Time`) VALUES
(1, 1, 1, 1, 10, 85000.00, '2024-08-01', '10:30:00'),
(2, 1, 2, 2, 15, 78000.00, '2024-08-05', '14:00:00'),
(3, 2, 4, 2, 20, 92000.00, '2024-08-10', '11:15:00'),
(4, 3, 6, 1, 30, 18000.00, '2024-08-12', '16:45:00'),
(5, 3, 8, 3, 50, 11000.00, '2024-08-18', '09:00:00');

INSERT INTO `inventory` (`Product_ID`, `Warehouse_ID`, `Quantity`) VALUES
(1, 1, 8),
(2, 2, 14),
(3, 1, 5),
(4, 2, 18),
(5, 3, 9),
(6, 1, 25),
(7, 4, 30),
(8, 3, 45),
(9, 4, 12),
(10, 1, 0);
