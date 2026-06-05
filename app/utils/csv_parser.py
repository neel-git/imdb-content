import csv

def stream_csv_batches(file_stream, batch_size: int = 1000):
    """ Yield batches of raw CSV rows as dicts without loading the full file. """

    def _decoded_lines(stream):
        for line in stream:
            yield line.decode("utf-8", errors="replace") if isinstance(line, bytes) else line

    reader = csv.DictReader(_decoded_lines(file_stream))
    batch = []
    for row in reader:
        batch.append(row)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch
