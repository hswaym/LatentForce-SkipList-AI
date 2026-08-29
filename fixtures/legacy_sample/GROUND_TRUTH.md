# Legacy Sample Ground Truth Test Oracle

This document records the exact expected status of all symbols in `fixtures/legacy_sample/`.

| File | Symbol | Status | Notes / Reasons |
| :--- | :--- | :--- | :--- |
| `app.py` | `main` | **Live** | Explicit CLI entry point (`if __name__ == "__main__": main()`). |
| `orders.py` | `create_order` | **Live** | Called directly by `app.main`. |
| `orders.py` | `cancel_order` | **Dead** | Defined but never called anywhere in the codebase. |
| `payments.py` | `charge` | **Live** | Called directly by `orders.create_order`. |
| `payments.py` | `deprecated_refund` | **Dead** | Defined but never called anywhere in the codebase. |
| `formatting.py` | `format_amount` | **Live** | Called directly by `payments.charge`. |
| `legacy_format.py` | `render_amount` | **Dead / Duplicate** | Never called anywhere. Structurally identical duplicate of `formatting.format_amount`. |
| `dispatch.py` | `run_action` | **Live** | Called directly by `app.main`. |
| `dispatch.py` | `export_data` | **Needs-review (Dynamic)** | Resolved dynamically via `getattr(sys.modules[__name__], name + "_data")` in `dispatch.run_action("export")`. Statically looks dead. |
| `dispatch.py` | `import_data` | **Needs-review (Dynamic)** | Handler for dynamic dispatch. Statically looks dead. |
| `unused_module.py` | `orphan_one` | **Dead** | Module `unused_module.py` is never imported by any reachable module. |
| `unused_module.py` | `orphan_two` | **Dead** | Module `unused_module.py` is never imported by any reachable module. |
