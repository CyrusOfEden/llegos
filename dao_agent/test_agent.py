



# agent = AutoGPTAgent()
# actor = Actor.remote(agent=AutoGPTAgent())
# future = actor.inform.remote("You are a robot.") # => future
# response = ray.get(future)


# agent = AutoGPTAgent()
# agent.start() # => required to call the future method, otherwise not needed
# future = agent.future("request", "You are a robot.") # => future
# response = ray.get(future)
