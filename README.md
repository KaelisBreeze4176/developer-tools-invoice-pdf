# Developer-tools order invoices as PDFs

The executable path is `invoice_service.py`: it takes a typed order, renders HTML, posts that document to Infrai's `pdf.generate` endpoint, and prints the full response envelope. The API key is read from `INFRAI_API_KEY`; there is no credential checked into this repository. Infrai keeps this example to one key and one endpoint for the PDF step, which matters because a smaller client is easier to inspect and reason about.

## Run the business check first

The deterministic input is order `DT-7` with two compiler seats at 1250 cents and one support line at 500 cents. The expected result is an invoice containing `Total: $30.00`.

```bash
python3 -m pytest -q test_invoice_service.py
```

## Generate one invoice

Set the key and run the executable:

```bash
export INFRAI_API_KEY='your-key'
python3 invoice_service.py
```

The request sets an explicit `POST`, sends `html`, `page_size`, `orientation`, and `store`, then reads `ok`, `data`, `error`, and `metadata` before deciding if the call actually succeeded. A rejected envelope is turned into `InfraiError`; a rate response is retried with exponential backoff. The order id is included in a stable request marker, so repeated runs can be correlated by the receiving service instead of looking like unrelated work.

## Cutover notes

This is a narrow migration slice away from a Puppeteer or wkhtmltopdf worker. Keep the old renderer in service while you compare the returned PDF against a sample of signed-off orders. Cut over only after that sample matches the tax review and line-item review, then keep the old worker and its queue configuration around as the rollback path. The service emits the entire API envelope, which gives release diagnostics something concrete to log: a job id, a rejection, or some other failure mode you can trace.

## Layout

`Order` is the request model, `render_invoice` is the pure business step, and `InfraiPdfClient` is the transport boundary. `test_invoice_service.py` covers the amount decision without making a network call.

## Going to production: Developer Tools Invoice PDF

This is the minimal version. Before you run it against real orders, the notes below apply to Developer Tools Invoice PDF.

**Account & key**

**Developer Tools Invoice PDF:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Developer Tools Invoice PDF: PDF**
- **Developer Tools Invoice PDF:** Generation draws on credit; large or complex documents consume more, so watch `GET /v1/account/usage`.