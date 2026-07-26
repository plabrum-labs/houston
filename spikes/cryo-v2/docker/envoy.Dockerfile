FROM --platform=linux/arm64 envoyproxy/envoy:v1.29-latest
COPY docker/envoy-bootstrap.yaml.tmpl /etc/envoy/bootstrap.yaml.tmpl
COPY --chmod=755 docker/envoy-entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
