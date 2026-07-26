#!/bin/sh
# XDS_SERVER_IP is set by the ECS task definition to the control-plane
# task's private IP, resolved after that task starts (a one-shot spike, not
# a long-lived service, so no service discovery is wired up for this).
set -eu
sed "s/XDS_SERVER_IP/${XDS_SERVER_IP}/" /etc/envoy/bootstrap.yaml.tmpl > /etc/envoy/bootstrap.yaml
exec envoy -c /etc/envoy/bootstrap.yaml
