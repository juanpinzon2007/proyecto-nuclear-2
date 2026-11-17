"""Servidor SMTP local de desarrollo (LAB_LOOPBACK) para capturar correos salientes RF-21 / RF-27."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path

HOST = "127.0.0.1"
PORT = 1025
LOG_FILE = Path(__file__).resolve().parent / "dev_mail_outbox.log"


async def handle_smtp(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    writer.write(b"220 sps-dev-smtp Service Ready\r\n")
    await writer.drain()

    sender = ""
    recipients: list[str] = []
    in_data = False
    data_lines: list[bytes] = []

    try:
        while True:
            raw = await reader.readline()
            if not raw:
                break

            if in_data:
                if raw in (b".\r\n", b".\n"):
                    in_data = False
                    body = b"".join(data_lines).decode("utf-8", errors="replace")
                    stamp = datetime.now(timezone.utc).isoformat()
                    entry = (
                        f"=== EMAIL [{stamp}] FROM={sender} TO={','.join(recipients)} ===\n"
                        f"{body}\n"
                        f"=== END EMAIL ===\n\n"
                    )
                    with LOG_FILE.open("a", encoding="utf-8") as fh:
                        fh.write(entry)
                    print(f"[SMTP] Correo recibido FROM={sender} TO={','.join(recipients)}", flush=True)
                    data_lines.clear()
                    writer.write(b"250 2.0.0 OK accepted\r\n")
                else:
                    if raw.startswith(b".."):
                        raw = raw[1:]
                    data_lines.append(raw)
                await writer.drain()
                continue

            line = raw.decode("utf-8", errors="replace").strip()
            upper = line.upper()
            if upper.startswith("EHLO") or upper.startswith("HELO"):
                writer.write(b"250-sps-dev-smtp\r\n250 OK\r\n")
            elif upper.startswith("MAIL FROM:"):
                sender = line[10:].strip().strip("<>")
                writer.write(b"250 OK\r\n")
            elif upper.startswith("RCPT TO:"):
                recipients.append(line[8:].strip().strip("<>"))
                writer.write(b"250 OK\r\n")
            elif upper == "DATA":
                in_data = True
                data_lines.clear()
                writer.write(b"354 End data with <CR><LF>.<CR><LF>\r\n")
            elif upper == "RSET":
                sender = ""
                recipients.clear()
                data_lines.clear()
                writer.write(b"250 OK\r\n")
            elif upper == "NOOP":
                writer.write(b"250 OK\r\n")
            elif upper == "QUIT":
                writer.write(b"221 Bye\r\n")
                await writer.drain()
                break
            else:
                writer.write(b"500 Unknown command\r\n")
            await writer.drain()
    finally:
        writer.close()


async def main() -> None:
    server = await asyncio.start_server(handle_smtp, HOST, PORT)
    print(f"SMTP dev sink listening on {HOST}:{PORT} -> {LOG_FILE}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
