# DreamNet BGP Containerlab

This lab provides three FRR routers and four controlled fault scenarios for the BGP procedural
graph. It uses Containerlab's native `frr` kind and the pinned
`quay.io/frrouting/frr:containerlab-10.7.1` image.

## Requirements

- Docker
- Containerlab
- Python 3.11+

## Deploy and verify the healthy baseline

```bash
cd lab/bgp
sudo containerlab deploy -t dreamnet.clab.yml
docker exec clab-dreamnet-bgp-r1 vtysh -c 'show bgp summary'
docker exec clab-dreamnet-bgp-r2 vtysh -c 'show bgp summary'
```

Both sessions should converge before fault injection.

## Run a fault and investigate it

```bash
python scenario.py apply asn_mismatch
dreamnet bgp-run \
  --live \
  --incident lab-asn-001 \
  --expected-prefix 192.0.2.1/32 \
  --output ../../artifacts/bgp-live
python scenario.py reset asn_mismatch
```

Available scenarios:

- `interface_down`
- `asn_mismatch`
- `neighbor_shutdown`
- `route_map_filter`

Always reset a scenario before applying another one. These mutations target only the local lab
containers and must not be reused against production devices.

## Destroy

```bash
sudo containerlab destroy -t dreamnet.clab.yml --cleanup
```
