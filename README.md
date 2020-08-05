# ProxyGenerator
A library class that crawls websites that provides free proxies and tests them for validity on a specific site. 
Class object then turns into a generator factory that provides the proxy.

## Usage
Create a new generator class through
```py
generator = ProxyGenerator('http://www.IAmATestingLink.com')
```
And acquire new proxies by
```py
generator.GetProxy()
```
On first call, the program will likely pause and the generator will need to completely populate and test all the proxies on first run. Subsequent background populations will not wait the program.


## Multithreaded interface
```py
generator.CrawlThread(target=target_function, args = [arg1, arg2...])
```
Automatically start or wait independent threads limited to the number of proxies available.

## Error Handling
```py
generator.HandleError(error, proxy)
```
Is called when a thread creates an error. If the error is proxy related, it will log the error internally and return. If it is not proxy related, it will reraise the exception.
If a proxy gets errored too many time, the proxy will be taken out of circulation.

## Automatical proxy renewals
Every 20 minutes, or when the available proxy count falls below 20 (normally due to proxies accumulating errors over time), the generator will recrawl the websites for new proxies, and transparently add them to the list in the background.

