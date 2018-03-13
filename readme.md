A website for user made question and answers.  Used for studying or trivia. Perhaps a homework system.
Written in Python3 using the Pyramid framework with sqlalchemy and postgresql (psycopg2) as the backend.

To create a new question type (work in progress and subject to change):
    In models.py
1.  Create a new class inheriting from Question and define the desired columns, relations, and constraints.

2.  create - Define the create method if you have any special processing that needs to be done. Otherwise, as long as
    the form for the model when validated produces a dictionary that can be expanded with ** to create a SQLAlchemy
    instance of your question, the superclass create method will suffice.

3.  edit - The same requirements as the create method.

4.  edit_schema - Define the edit_schema method.  If the schema definition follows the existing way of defining the
    schemas (a base class, a sequencewidget class, and the sequencewidget container class) then a step(s) in the
    forms.py section will make it so the base class instance will be merged with a csrf protection schema by
    the superclass method.

5.  report - Define the report method, which should return HTML code that tells the user whether their answer
    was right or wrong

6.  handle_db_exception - Define the handle_db_exception method which handles exceptions specific to the new
    question type.  Should be defined even if no exceptions specific to your class need to be handled in case
    some unknown issue falls through.  This method should raise a ValueError.

7.  Add an entry for the question to the QuestionType Enum and add a case to the get_question_class method in said Enum class.

8.  Add the new question type to Question.LOAD_COMPLETE_POLYMORPHIC_RELATION's list argument which is the last line in the module.
