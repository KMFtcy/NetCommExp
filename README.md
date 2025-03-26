# NetCommExp - Network Communication Xeperiment

This project is to explore the impact of different network transport protocol designs on performance metrics under different network conditions.

## Tests

Run all tests in the tests directory.
```bash
python -m unittest discover -s tests
```

## Examples

Run the example program.

Run the server.
```bash
python examples/mini_tcp_message_transmit.py server
```

In another terminal, run the client.
```bash
python examples/mini_tcp_message_transmit.py client
```