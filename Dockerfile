# Glama collects a server in a container and wraps it in mcp-proxy, so it expects
# stdio, not HTTP. Same five functions as the CLIs, different transport.
FROM python:3.12-slim AS build
WORKDIR /app
COPY pyproject.toml README.md ./
COPY nidhipati_proof ./nidhipati_proof
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim
WORKDIR /app
COPY --from=build /install /usr/local
RUN useradd --create-home --uid 10001 nidhipati
USER nidhipati
# No EXPOSE: this is a stdio server, it opens no port.
LABEL io.modelcontextprotocol.server.name="io.github.mrpkk/nidhipati"
ENTRYPOINT ["python", "-m", "nidhipati_proof.mcp_stdio"]
