# **Internship-TBI**
Here I will be adding my learnings during my summer internship of 2026.

## **Day 1** [📁](Practice_task_01) <br>
I completed the task which was simple use of comman function and attributes of pandas with some conditional statements on a edtech company dataset problem. as it was first day nothing major was done in learning aspect as it was majorly used in geting the documentation done and getting friently with the enviornment.

## **Day 2** [📁](Practice_task_02)<br>
I completed the task of fintech company dataset which was using of many other concepts of python programming and pandas. Here I worked with typecasting of the integers , strings and datetime to satisfy the given requirements. Also I used some string formatting to bring the data in required form, also handled the null values of different kinds, at last the numerical columns(eg: age, salary) were filled by median and trhe categorical data was filled by word "Unknown" and the unknown dates were filled by a default date. In date column some dates were written like dd/mm/yyy and some were dd-mm-yy, pandas by defraulty recoganises - not / so i chnaged / to - so that there was no loss of data, it was not mentioned in the problem statement but was observered by exploring the data, this was 1 of lessons i learned that knowing and understanding data is very important as this will enhance your work quality.

## **Day 3** [📁](Practice_task_03)<br>
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

## **Day 4** [📁](Practice_task_04)<br>
Today I started some EDA on my project which is for IITM MLP Project which is heavy equipment selling price prediction I am working on it in kaggle. Also I did the task for day 4 it was very basic problem to make functions with using concepts of loops, list and tuples.

## **Day 5** [📁](Practice_task_05)<br>
Today I worked on databases I was provided a documnet which wanted to make a database of 12 tables with multiple columns which are interconnected and have their specific data types and default values. I also had to make ENUMs which are the custom datatypes for storing the data like status (active/inactive), preffered_language (en,tr). <br>
Here is: 
* What i understood from the document was that it is a multi company employee feedback platform.
* It has a proper schema for keeping the records of employees and their feedbacks with complete technical architecture.
* The system is designed to handle employees feedback using mobile app and use AI to display the results on admin dashboard.
* The system needs an organizational heirarchy, feedback collection, AI preprocessing & analytics and notifications.
* Platform’s proper operational flow of data is provided for secure processes and data storage.
<br> <br>
I have added the SQL dump file in the repo for refference.

## **Day 6** [📁](Practice_task_06)<br>
Today I continoued on last task and build a simple signup page for employees using flask and connected it to the db with fully secure hashing method makeing it an end to end product without css :) i have attached the python code and demo video link in the repo.

## **Day 7** [📁](Practice_task_07)<br>
Today I continoued on the last task and made a login page making my project multipage and also I used JOIN to print infop of other tables when the employee logs in, i have attached the code and the demo video link. After that I was told to make an update section too that when the employee logs in then there will be a button for update details there he can change it as he wants, I have attacheed its video link too. The code attached is the final code.

## **Day 8** [📁](Practice_task_08)<br>
Today I continoued on the last task and I build feedback viewing page. So I filled tables like questions, and feedback related tables with some dummy data and then build feedback page in my python app. I have attached the code and the demonstraion video link in the repo.

## **Day 9** [📁](Practice_task_09)<br>
Today I was given a mini task in pandas, it was a simple groupby and aggregation task then I was instructe4d to continue on the last task and today I was said to make CRUD operation of companies and its departments and on which I have completed the companies part and still working on the departments and will complete it by tommorow.

## **Day 10** [📁](Practice_task_10)<br>
Today I completed the last task to  make CRUD for departments and afterwards i was told to make CRUD for questions too so I make that, I had to keep question limit of 3 for every company. I made an extra feature of "All Department" during selection of question for department for convenience ;) I have attached the code and the demo video links to the repo for the same.

## **Day 11** 📁<br>
Today I visited about the basics of api develoopment i learned about the https and its protocal, the different types of requests like GET, POST, PATCH, PUT and DELETE. Also I saw multiple types status codes like 1xx -> Inforamtional, 2xx -> success, 3xx -> redirection, 4xx -> Client error, 5xx -> Server error. Also I looked abut the headers and the body along with JSON and handling it using python serialization and deserialization and at last I saw abou the various api testers and its needs.

## **Day 12** [📁](Practice_task_12)<br>
Today I made further more changes in the last task and make some changes in signup section and made it covinient to use by adding a drop down for company and department instead of adding a long uuid and also i added re-entre the passwword for confirmation from user side about the password. Then I added a new section abou the feedback submission for daily basis for the questions of the departmnet you are in that company. Also i fixed the order id og quesions and made that the last question for same order id will get the order id and the other will get the remaining index which is left. I have attached the demo video for it.

## **Day 13** 📁<br>
Today I moved forward and learned about RAG, in it I covered the different vector dbs, different chunking stratagies and late chunking. Further I covered Contextual Retrieval, Hybrid Search, Reranking, Query Augmentation, Semantic Caching, Multimodal Embeddings and GraphRAG with their details. Also I covered the RAGAS Evaluation and its 4 metrics for evaluation.

## **Day 14** [📁](Practice_task_14)<br>
Today I continues in my project and added an admin portal which has access of editing companies, employees, department and questions in which user management page I added search and sort using names or emails using recent or alphabet order. Also I created the feature of editing your past feedback which only the user can perform CRUD not even the admin. I have attached the demo video link and the code.

## **Day 15** 📁<br>
Today I covered the Basics of Agentic AI what is it and its usecases in it i covered tool calling, agentic memory systems, multiagent systems, specialized agents, MCPs, need of async and parllelism and the importance of LXD Sandboxing along with the agent evaluation. Then I studied about the Agentic AI Guardrails and its types, what are its importances at different levels.

## **Day 16** [📁](Practice_task_16)<br>
Today I made Analytics page which had 6 graphs: <br>
1) Feedback Sentiment Breakdown it is a pie chart of positive neutral and negative feedback sentiments.
2) Feedback Volume by Department which is a bar chart having number of feedback from each department
3) Employees per Company which is a pie chart showing the number of employees from very company
4) Departments per Company it is a bar chart showing the number of departments from each company
5) Feedback Submissions Over Time it is a time series line chart showing the trend of submissions on each day
6) Distribution of Answer Lengths it is a histogram of character count of the submissions <br>
<br>
I have attached the demo video link and code in the repo.

## **Day 17** 📁<br>
Today I covered the multiple use case, features and services of langchain. I covered the multiple components of langchain: models, prompts, chains, memory, indexes and agents. I explored every component in detail with code demonstrations and therefore understanding the implementation of the features covered during studying RAG, except that I covered the model loading and using it, different types of prompts and templates. Also I covered the different ways for keeping memory and then I covered different ways to structure the output of a chat model using typed dict, pydantic or in json.

## **Day 18** [📁](Practice_task_18)<br>
Today I moved forward on the employee feedback site and made a reports page for admin portal which carries the information of no. of companies, departments, eymployees, questions and feedbacks. The feedback submission can be filtered with the time like last week, last month or custom dates. Also I added export to csv feature in all the tables accross the website like in user management, company management, department management and question management. I have attached the demo link and code for the same.

## **Day 19** 📁<br>
Today I covered the topic of multi agents and their working, First of all I covered the identification and authentication through DIDs encryption through mTLS and then for working i can to know about llm based semantic search for agent selection or hard coded agent selection and the JSON schema handover that the worker agent gives the full schema of what it needs before doing task. Then i covered the multiple protocols and their usecases I covered gRPC, websockets and MQTT protocols. Then I covered context passing mechanisms that how to pass context between agents in which state hydration was a great way it gives the tread id to the other agent and then that agent takes relevant data from the server where data is in this was context window is not polluted and then I covered the different types of agent coordination like centralized and decentralized what are their pros and cons the way they route to other agents. Then I covered the memory Management and Context Control in which for memory dual architecture is used which is working memory and long term memory  and for summarization rather than making of full data make it for chunks and then get key points and put them in key value pairs and then merge all data in state summary object. 

## **Day 20** [📁](Practice_task_20)<br>
Today I continued on employee feedback project and made translator for french I used babel for the having the translatoin of the text on the site and also I made a Content Translation Management page for admin accounts so that they can edit and save the transtation of the questions for feedback. The interface can be changed between english and french by using a drop down on the navbar. the code and the demo video is been attached.

## **Day 21** 📁<br>
I worked extensively on deployment and cloud infrastructure technologies. I learned about GitHub as a version control system for maintaining code, utilizing features like branching, merging, rollback capabilities, and collaborative workflows to manage code versions effectively. I explored Vercel as a deployment platform for frontend applications, enabling quick deployment with automatic builds and preview environments. I studied AWS (Amazon Web Services) for online hosting and cloud infrastructure, learning how to provision and manage cloud resources for backend services and scalable application deployment. I understood CI/CD (Continuous Integration/Continuous Deployment) pipelines and their importance in automating the testing, building, and deployment processes, ensuring code quality and reducing manual deployment efforts across different environments. I learned how these tools work together in a complete DevOps workflow—using GitHub for code management, CI/CD pipelines for automated testing, AWS for hosting backend infrastructure, and Vercel for frontend deployment.
