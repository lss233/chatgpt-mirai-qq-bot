import asyncio


async def evaluate_array(array):
    """Evaluate all coroutines in an array and return a new array with the results."""
    coroutines = []
    positions = []
    # Check each value in the array
    for i in range(len(array)):
        value = array[i]
        if asyncio.iscoroutine(value):
            # Add the coroutine and its position to the list of coroutines to run in parallel
            coroutines.append(value)
            positions.append(i)
    # Run all coroutines in parallel using gather
    if coroutines:
        evaluated = await asyncio.gather(*coroutines)
        # Replace the coroutines with their evaluated values in the original positions
        for i in range(len(positions)):
            array[positions[i]] = evaluated[i]
    return array
