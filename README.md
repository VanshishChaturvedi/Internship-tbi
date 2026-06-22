# **Internship-tbi**
Here i will be adding my learnings during my summer internship of 2026.

## **Day 1** <br>
I completed the task which was simple use of comman function and attributes of pandas with some conditional statements on a edtech company dataset problem. as it was first day nothing major was done in learning aspect as it was majorly used in geting the documentation done and getting friently with the enviornment.

## **Day 2** <br>
I completed the task of fintech company dataset which was using of many other concepts of python programming and pandas. Here I worked with typecasting of the integers , strings and datetime to satisfy the given requirements. Also i used some string formatting to bring the data in required form, also handled the null values of different kinds, at last the numerical columns(eg: age, salary) were filled by median and trhe categorical data was filled by word "Unknown" and the unknown dates were filled by a default date. In date column some dates were written like dd/mm/yyy and some were dd-mm-yy, pandas by defraulty recoganises - not / so i chnaged / to - so that there was no loss of data, it was not mentioned in the problem statement but was observered by exploring the data, this was 1 of lessons i learned that knowing and understanding data is very important as this will enhance your work quality.

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
