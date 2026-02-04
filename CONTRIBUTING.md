## Spec

The spec was found here: https://github.com/compose-spec/compose-spec/blob/main/schema/compose-spec.json

## Generate models

```sh
datamodel-codegen --input .\spec.json --output-model-type pydantic_v2.BaseModel --output pytest_testcontainers_compose/models/models.py
```
