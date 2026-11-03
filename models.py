# models.py
# This file defines the shape of the data the server accepts.
# Pydantic checks every incoming request against these rules.

from pydantic import BaseModel, Field  # BaseModel is the parent class for models. Field adds rules to a field.


class AskRequest(BaseModel):
    # The question must be text (str).
    # min_length=1 rejects an empty question.
    # max_length=2000 rejects very long input, which protects cost and speed.
    question: str = Field(
        min_length=1,
        max_length=2000,
        description="The application text or question to send to the model.",
        examples=["Ada Obi is a 300-level Computer Engineering student at the University of Uyo, applying for a Data Analyst internship starting 2 February 2027."],
    )

class AskResponse(BaseModel):
    # The reply always has these two fields.
    question: str = Field(description="The question that was received.")
    answer: str = Field(description="The model's reply, as text.")