# لسان | Lisan Programming Language

هذا المجلد مخصص لتطوير **لسان**، لغة برمجة عربية باستخدام **Rust**، ضمن مساحة مشاريع GITM-OS.

## حالة المشروع

- توجد نسخة مصدرية تجريبية `v0.2.0` محفوظة خارج هذا المستودع.
- هذا المجلد نقطة بداية لتنظيم المشروع على GitHub؛ **لم تُرفع الشيفرة المصدرية بعد**.
- المراحل التالية: استيراد شيفرة Rust، تشغيل `cargo test` عبر GitHub Actions، تطوير المكتبة القياسية، ثم بناء مترجم للبرامج التنفيذية.

## هيكل المشروع المخطط

```text
lisan-lang/
  Cargo.toml
  src/
  examples/
  tests/
  docs/
  .github/workflows/
```

> للتجربة بعد رفع الشيفرة: `cargo test` ثم `cargo run -- examples/hello.lsn`.
