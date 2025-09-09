


socket.onmessage = (event) => {
    debugLog('Message received', JSON.parse(event.data));
};
```

### Browser Compatibility

