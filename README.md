# Service 1 Final Project 2026

This repo currently implements only Service 1, the customer validation service.

## Triggering mechanism

Service 1 uses simple HTTP triggering. When `POST /process` is called, it:

1. Reads pending customer records from MongoDB.
2. Validates each record.
3. Stores only the validation result on each record.
4. Calls the next service by HTTP for valid records:
   - welcome letters -> `http://welcome_service:5001/generate`
   - offer letters -> `http://offer_service:5002/generate`

Because Services 2 and 3 are not implemented in this scope, trigger failures do not crash the validator and are not stored in MongoDB.

## Run

```bash
docker compose up --build
```

The validator connects to MongoDB Atlas using `MONGO_URI` from `.env`.

## Test the validator

Check health:

```bash
curl http://localhost:5000/health
```

Get one customer by account number:

```bash
curl http://localhost:5000/customer/12345678
```

Run validation:

```bash
curl -X POST http://localhost:5000/process
```

Reset all validation fields so the existing records can be processed again:

```bash
curl -X POST http://localhost:5000/reset-validation
```

## MongoDB record updates

Each processed customer gets only these validation fields:

- `is_valid`
- `validation_errors`

Use `POST /reset-validation` to clear those fields and any legacy validator fields for all customers already stored in Atlas.
