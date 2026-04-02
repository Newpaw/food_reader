import { describe, expect, it } from 'vitest';

import { groupMealsByDay } from '../history.js';


describe('history grouping', () => {
  it('groups meals into descending local-day buckets', () => {
    const grouped = groupMealsByDay([
      { id: 1, consumed_at: '2026-04-01T08:00:00Z' },
      { id: 2, consumed_at: '2026-04-01T18:00:00Z' },
      { id: 3, consumed_at: '2026-04-02T09:00:00Z' },
    ]);

    expect(grouped).toHaveLength(2);
    expect(grouped[0].meals.map((meal) => meal.id)).toEqual([3]);
    expect(grouped[1].meals.map((meal) => meal.id)).toEqual([2, 1]);
  });
});
