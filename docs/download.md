# Download GITM OS 3.3 — Design update 1
[Download single ISO](https://gitm-os-download-33.naimamiam1234.workers.dev/GITM-OS-3.3.0-integration-amd64.iso?revision=design1)
[60 actual guest screenshots](https://gitm-os-download-33.naimamiam1234.workers.dev/gallery?revision=design1)
[GitHub release and split-file fallback](https://github.com/naimamiam1234-star/GITM-OS/releases/tag/gitm-os-3.3.0-design1)
[Arabic guide](design-build-ar.md)

ISO size: 3008622592 bytes.
SHA-256: `42f7822aef8c91e511fe793a41abdbef9193c905199d3dbd720b1741a3993133`.
BIOS/UEFI boot and the actual browser policy/window checks passed in [run 38017305438](https://github.com/naimamiam1234-star/GITM-OS/actions/runs/38017305438).
The screenshot album contains sixty freshly captured views from this ISO. Installation, Secure Boot and physical vehicle/device compatibility require separate tests.

On Windows, the fallback requires both part files and Join-ISO-Windows.cmd in the same directory; run the command file to assemble and verify the ISO. Do not mix parts from different releases.
On Linux, concatenate the two parts in numeric order and use the supplied SHA256 file to verify the result.
