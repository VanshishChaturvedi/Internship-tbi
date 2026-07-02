# **Internship-TBI**
Here i will be adding my learnings during my summer internship of 2026.

## **Day 1** <br>
I completed the task which was simple use of comman function and attributes of pandas with some conditional statements on a edtech company dataset problem. as it was first day nothing major was done in learning aspect as it was majorly used in geting the documentation done and getting friently with the enviornment.

## **Day 2** <br>
I completed the task of fintech company dataset which was using of many other concepts of python programming and pandas. Here I worked with typecasting of the integers , strings and datetime to satisfy the given requirements. Also I used some string formatting to bring the data in required form, also handled the null values of different kinds, at last the numerical columns(eg: age, salary) were filled by median and trhe categorical data was filled by word "Unknown" and the unknown dates were filled by a default date. In date column some dates were written like dd/mm/yyy and some were dd-mm-yy, pandas by defraulty recoganises - not / so i chnaged / to - so that there was no loss of data, it was not mentioned in the problem statement but was observered by exploring the data, this was 1 of lessons i learned that knowing and understanding data is very important as this will enhance your work quality.

## **Day 3** <br>
I Explored about the various methods if data cleaning and combined my todays learnings with my prior knowledge to understand the topic. I came to know of these points for data cleaning:
* **Handling Missing Data** : The nan values can be simply drop if the occuring is rare but if the ouccrance is significant we have to replace it with either mean, median, mode or a default value also we can use interpolate function according to the use case. Also we can use KNN which is a ML model it can replace the nan values the nearest data points (similar to it).
* **Handling Duplicates** : This can be simply handled by using .duplicate() function we can control the working of function by using the paramenters like keep and give the desired columns with subset paramenter.
* **Typecasting in Correct Datatype** : We can do that be use of .astype(), pd.to_numeric(), pd.to_datetime(), .astype('category'). the category type is used to optimize the code it is used when the cardinality of the column entries is low. error='coerce' is a very usefull parameter to handle the wrong entries in the numerical and date columns it safely changes them to nan and nat respectively.
* **Standardizing the Text** : We use str.strip(), str.replace(old, new), str.lower(), str.upper(), str.title(), str.capitalize() to keep the format standard.
* **Altering the Shape of Data** : We use pd.melt() to change the datafram from wide to long and use df.pivot() for inverse.
* **Spliting and Merging Columns** : It is simply feature engineeirng to exract column as you want.
* **Handling Outliers** : They can be identified using IQR and we can either drop them or replacve with the min or max acceptebe value cap.
* **Handling Invalid Data** : This can simply use conditionals to filterout the invalid entires and replace it with nan and handle it with other nan values.
* **Encoding the Categorical Data** : It is done to canvert the categorical data into numerical because ML models only get numbers so we do one hot encoding for nominal data and ordinal encoding for the ordinal data. Also we do label encoding for the labels.
<br>
And for my todays practice task it was to handle multiple datasets at same time. I already have worked on such problems whlie learning SQL but it was long time ago so it was refreshing handling such porblems again. Today I had to inner join and left join the datasets and then to filtering and then averaging using .groupby(). The key point in todays PS was to complete the task by using a chained workflow, so I first wrote the sode as usual and then built a chained workflow as required.

## **Day 4** <br>
Today I started some EDA on my project which is for IITM MLP Project which is heavy equipment selling price prediction I am working on it in kaggle. Also I did the task for day 4 it was very basic problem to make functions with using concepts of loops, list and tuples.

## **Day 5** <br>
Today I worked on databases I was provided a documnet which wanted to make a database of 12 tables with multiple columns which are interconnected and have their specific data types and default values. I also had to make ENUMs which are the custom datatypes for storing the data like status (active/inactive), preffered_language (en,tr). <br>
Here is: 
* What i understood from the document was that it is a multi company employee feedback platform.
* It has a proper schema for keeping the records of employees and their feedbacks with complete technical architecture.
* The system is designed to handle employees feedback using mobile app and use AI to display the results on admin dashboard.
* The system needs an organizational heirarchy, feedback collection, AI preprocessing & analytics and notifications.
* Platform’s proper operational flow of data is provided for secure processes and data storage.
<br> <br>
> *I have added the SQL dump file in the repo for refference.*

## **Day 6** <br>
Today I continoued on last task and build a simple signup page for employees using flask and connected it to the db makeing it an end to end product without css :) i have attached the python code and demo video link in the repo.

## **Day 7** <br>
Today I continoued on the last task and made a login page making my project multipage and also I used JOIN to print infop of other tables when the employee logs in, i have attached the code and the demo video link. After that I was told to make an update section too that when the employee logs in then there will be a button for update details there he can change it as he wants, I have attacheed its video link too. The code attached is the final code.

## **Day 8** <br>
Today I continoued on the last task and I build feedback viewing page. So I filled tables like questions, and feedback related tables with some dummy data and then build feedback page in my python app. I have attached the code and the demonstraion video link in the repo.

## **Day 9** <br>
Today I was given a mini task in pandas, it was a simple groupby and aggregation task then I was instructe4d to continue on the last task and today I was said to make CRUD operation of companies and its departments and on which I have completed the companies part and still working on the departments and will complete it by tommorow.

## **Day 10** <br>
Today I completed the last task to  make CRUD for departments and afterwards i was told to make CRUD for questions too so I make that, I had to keep question limit of 3 for every company. I made an extra feature of "All Department" during selection of question for department for convenience ;) I have attached the code and the demo video links to the repo for the same.

## **Day 11** <br>
Today I visited about the basics of api develoopment i learned about the https and its protocal, the different types of requests like GET, POST, PATCH, PUT and DELETE. Also I saw multiple types status codes like 1xx -> Inforamtional, 2xx -> success, 3xx -> redirection, 4xx -> Client error, 5xx -> Server error. Also I looked abut the headers and the body along with JSON and handling it using python serialization and deserialization and at last I saw abou the various api testers and its needs.
