const TROUBLESHOOT_ENDPOINT = "/api/v1/troubleshoot";


export async function troubleshoot(query) {

  const response = await fetch(
    TROUBLESHOOT_ENDPOINT,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        query: query,
      }),
    }
  );


  const data = await response.json();

  if (!response.ok) {
    throw new Error(
      data?.message || "Troubleshooting failed"
    );
  }

  return data;
}