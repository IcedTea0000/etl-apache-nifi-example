# **etl-apache-nifi-example**
This is a example of ETL task using Apache Nifi, MySQL, Python naitive

---
### **Context Description**
- 2 database **Olist** and **NewMart**. The goal is to detect any update in table **olist.olist_customers_dataset** of customer_number list in NewMart db, extract all information related to the customer_number list from 4 Olist tables, convert information to JSON object, publish to Kafka for consumption. 
 
---
### **Result Example** 

- table newmart.cif_client

| client_id |
| --- |
| 060e732b5b29e8181a18229c7b0b2b5e |

- table olist.olist_customers_dataset

| customer_unique_id |
| --- |
| 060e732b5b29e8181a18229c7b0b2b5e |
| 290c77bc529b7ac935b93aa66c333dc3 |

- Today **olist.olist_customers_dataset** has 2 update **060e732b5b29e8181a18229c7b0b2b5e, 290c77bc529b7ac935b93aa66c333dc3**

- Nifi job will detect these updates and convert information of id **060e732b5b29e8181a18229c7b0b2b5e** to JSON object with new mapping. This JSON object will then be published to Kafka:
```
[ {
  "customer_number" : "060e732b5b29e8181a18229c7b0b2b5e",
  "oder_info" : [ {
    "order_id" : "5741ea1f91b5fbab2bd2dc653a5b5099",
    "product_id" : "0be701e03657109a8a4d5168122777fb",
    "price" : "259.90",
    "review_id" : "9a6614162d285301aa3ef6de4be75265",
    "review_score" : "5",
    "review_content" : ":Loja responsÃ¡vel"
  }, {
    "order_id" : "98b737f8bd00d73d9f61f7344aadf717",
    "product_id" : "223d34a3d9334039f5ff9511dc044bbb",
    "price" : "246.62",
    "review_id" : "fd0e493eac47b2e64aec60efcb2b3dc2",
    "review_score" : "5",
    "review_content" : ":Produtos de primeira linha."
  } ]
} ]
```

---
### **Job Flow** 
- Apache Nifi Template layout

![Apache Nifi Template layout](https://github.com/IcedTea0000/etl-apache-nifi-example/blob/master/document_img/template_overview.JPG)

- Setup environment:The Database ddl file and data is stored in ..\setup_environment. Import data from csv files to database. Enable binary logging feature of MySQL by adding the following to the [mysqld] section of the my.ini config file
```
server_id = 1
log_bin = delta
binlog_format=row
binlog_do_db = olist
binlog_do_db = newmart
```

For this Nifi job, it requires the current user having mysql_native_password authentication method. This is not by default config when a MySQL 8 user was created. To do this, run this query
```
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password';
--Where 'root' as your user 'localhost' as your URL and 'password' as your password

FLUSH privileges;
```

**The rest of the job flow will be explained with example data**

- Processor CaptureChangeFromDBBinlog: check the binary logs for any changes. Output the new update information.
Ex: 
Today, changes in db olist and newmart are:

```
UPDATE `olist`.`olist_customers_dataset`
SET `customer_city` = 'sao paolo'
WHERE customer_unique_id = '4c93744516667ad3b8f1fb645a3116a4';

INSERT INTO `newmart`.`cif_client` (`client_id`) VALUES ('4c93744516667ad3b8f1fb645a3116a4');
INSERT INTO `newmart`.`cif_client` (`client_id`) VALUES ('290c77bc529b7ac935b93aa66c333dc3');
```

Outputs of this processor  are 4 flowfiles. With format:
```
{
  "type" : "insert",
  "timestamp" : 1595964046000,
  "binlog_filename" : "DESKTOP-0O951IU-bin.000001",
  "binlog_position" : 9481,
  "database" : "newmart",
  "table_name" : "cif_client",
  "table_id" : 110,
  "columns" : [ {
    "id" : 1,
    "name" : "client_id",
    "column_type" : 12,
    "value" : "4c93744516667ad3b8f1fb645a3116a4"
  } ]
}
```
- Processor AddAttributeDatabaseToFlowFile: add attributes 'database' and 'table_name' to flowfiles from the queue.
- Processor RouteOnAttributeDatabase: route flowfiles to different branches depend on their attribute 'database', 'table_name', and 'cdc.event.type'
- Processor ExtractFlowFileContent: extract only the content of flowfiles (which are records from database)

Example: 
Output of data from olist db are:
```
[ {
  "customer_id" : "879864dab9bc3047522c92c82e1212b8",
  "customer_unique_id" : "4c93744516667ad3b8f1fb645a3116a4",
  "customer_zip_code_prefix" : "89254",
  "customer_city" : "sao paolo",
  "customer_state" : "SC"
} ]
```

Output of data from newmart db are:
```
[{"client_id":"4c93744516667ad3b8f1fb645a3116a4"}]
```

- Processor Script_ExtractNewmartCustNo and Script_ExtractOlistCustNo: extract the customer_id from olist data and client_id from newmart data

Example:
Output of data from olist db are:
```
4c93744516667ad3b8f1fb645a3116a4
```

Output of data from newmart db are:
```
4c93744516667ad3b8f1fb645a3116a4
```

- Processor Script_FilterCustNoList: detect if input is newmart data then save the input cust_no list to processor state 'newmartCustList'. If input is olist data, filter this data with cust_no list from processor state 'newmartCustList'. The output is a cust_no list that both exists in 2 databases.

Example:
```
4c93744516667ad3b8f1fb645a3116a4
```

- Processor QuerySLRecords: query the left join records of the cust_no input, and return all required information associate with that cust_no from olist db.

Example:
Output of this processor:
```
[ {
  "customer_unique_id" : "4c93744516667ad3b8f1fb645a3116a4",
  "order_id" : "98b737f8bd00d73d9f61f7344aadf717",
  "product_id" : "223d34a3d9334039f5ff9511dc044bbb",
  "price" : "246.62",
  "review_id" : "fd0e493eac47b2e64aec60efcb2b3dc2",
  "review_score" : "5",
  "review_comment_title" : "",
  "review_comment_message" : "Produtos de primeira linha."
}, {
  "customer_unique_id" : "4c93744516667ad3b8f1fb645a3116a4",
  "order_id" : "5741ea1f91b5fbab2bd2dc653a5b5099",
  "product_id" : "0be701e03657109a8a4d5168122777fb",
  "price" : "259.90",
  "review_id" : "9a6614162d285301aa3ef6de4be75265",
  "review_score" : "5",
  "review_comment_title" : "",
  "review_comment_message" : "Loja responsÃ¡vel"
} ]
```

- Processor Script_MergeJson: re-arrange the input to create a JSON object with requirement mappings.

Example:
Output of this processor:
```
[ {
  "customer_number" : "4c93744516667ad3b8f1fb645a3116a4",
  "order_info" : [ {
    "review_id" : "fd0e493eac47b2e64aec60efcb2b3dc2",
    "review_content" : " Produtos de primeira linha.",
    "price" : "246.62",
    "review_score" : "5",
    "product_id" : "223d34a3d9334039f5ff9511dc044bbb",
    "order_id" : "98b737f8bd00d73d9f61f7344aadf717"
  }, {
    "review_id" : "9a6614162d285301aa3ef6de4be75265",
    "review_content" : " Loja responsÃ¡vel",
    "price" : "259.90",
    "review_score" : "5",
    "product_id" : "0be701e03657109a8a4d5168122777fb",
    "order_id" : "5741ea1f91b5fbab2bd2dc653a5b5099"
  } ]
} ]
```

- Processor PublishKafka_2_0: publish the JSON object above to Kafka.

---
### **References**

[Series Change Data Capture (CDC) with Apache NiFi](https://community.cloudera.com/t5/Community-Articles/Change-Data-Capture-CDC-with-Apache-NiFi-Part-1-of-3/ta-p/246623)

[NiFi Scripting Samples](https://github.com/BatchIQ/nifi-scripting-samples)

[Series ExecuteScript Cookbook](https://community.cloudera.com/t5/Community-Articles/ExecuteScript-Cookbook-part-1/ta-p/248922)
