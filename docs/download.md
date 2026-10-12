# Download GITM OS 3.3 — Design update 1
[Download single ISO](https://gitm-os-download-33.naimamiam1234.workers.dev/GITM-OS-3.3.0-integration-amd64.iso?revision=design2)
[60 actual guest screenshots](https://gitm-os-download-33.naimamiam1234.workers.dev/gallery?revision=design2)
[GitHub release and split-file fallback](https://github.com/naimamiam1234-star/GITM-OS/releases/tag/gitm-os-3.3.0-design2)
[Arabic guide](design-build-ar.md)

ISO size: 3008626688 bytes.
SHA-256: `209c6db062a550d61581c7688952763bdbcdc46b1c1e33759b7be342365a92f5`.
BIOS/UEFI boot and the actual browser policy/window checks passed in [run 38017305438](https://github.com/naimamiam1234-star/GITM-OS/actions/runs/38017305438).
The screenshot album contains sixty freshly captured views from this ISO. Installation, Secure Boot and physical vehicle/device compatibility require separate tests.

On Windows, the fallback requires both part files and Join-ISO-Windows.cmd in the same directory; run the command file to assemble and verify the ISO. Do not mix parts from different releases.
On Linux, concatenate the two parts in numeric order and use the supplied SHA256 file to verify the result.
