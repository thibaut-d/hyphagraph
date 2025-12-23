import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import { Entity } from "../types/domain";

export default function EntitiesView() {
  const [entities, setEntities] = useState<Entity[]>([]);

  useEffect(() => {
    apiGet<Entity[]>("/entities").then(setEntities).catch(console.error);
  }, []);

  return (
    <section>
      <h2>Entities</h2>
      <ul>
        {entities.map(e => (
          <li key={e.id}>
            {e.label} ({e.kind})
          </li>
        ))}
      </ul>
    </section>
  );
}