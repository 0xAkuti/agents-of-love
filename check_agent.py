from src.model import Agent
import sys

with open(sys.argv[1], "r") as f:
    try:
        agent = Agent.model_validate_json(f.read())
        print('Agent is valid')
    except Exception as e:
        print(e)
