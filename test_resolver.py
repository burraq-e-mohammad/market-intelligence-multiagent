import json
from agents.entity_resolver import EntityResolverAgent

agent = EntityResolverAgent()
target = input("Enter a company name or ticker to resolve: ").strip()
resolved = agent.resolve(target)
print(json.dumps(resolved.model_dump(), indent=2))
