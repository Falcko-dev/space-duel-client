import asyncio
import queue

async def main():
	a = queue.Queue()
	b = a.get()
	pass

if __name__ == '__main__':
	asyncio.run(main())