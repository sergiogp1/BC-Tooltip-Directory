# Contributing

Thank you for contributing to the BC Tooltip Directory!

## How to edit a field's tooltip

1. Open `data/tables/{table_slug}.json`.
2. Find the field by its `no` or `name`.
3. Edit the `tooltip` value.
4. Run `node scripts/generate_search_index.js` and commit.

## Table JSON schema

```json
{
  "id": 18,
  "name": "Customer",
  "slug": "18_customer",
  "objectNamespace": "Base Application",
  "description": "Optional description of the table.",
  "fields": [
    {
      "no": 1,
      "name": "No.",
      "tooltip": "Specifies the number of the record."
    }
  ]
}
```

### Field values

| Field | Description |
|---|---|
| `no` | AL field number (integer) |
| `name` | Internal AL field name |
| `tooltip` | The tooltip text shown in BC |

### Slug convention

`{tableId}_{table_name_snake_case}` — e.g. `18_customer`, `37_sales_line`.