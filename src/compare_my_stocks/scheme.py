from pydantic import TypeAdapter
from pydantic.json_schema import GenerateJsonSchema
#This scheme is used for intelisense only

class FastAPIGenerateJsonSchema(GenerateJsonSchema):
    """

    """

    def handle_invalid_for_json_schema(self, schema, error_info) :

        return {}


from config.newconfig import Config
t=TypeAdapter(Config)
jsonschema= t.json_schema(schema_generator=FastAPIGenerateJsonSchema)
import json
json.dump(jsonschema,open(r'data/myconfig.schema.json','wt'),indent=4)

