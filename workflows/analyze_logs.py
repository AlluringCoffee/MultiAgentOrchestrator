```python
   import sys
   import re
   from datetime import datetime

   def parse_logs(logfile):
       with open(logfile, 'r') as f:
           for line in f:
               if "ERROR" in line:
                   timestamp = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                   if timestamp:
                       print(f"Timestamp: {timestamp.group(1)} - {line.strip()}")
   parse_logs(sys.argv[1])
   ```