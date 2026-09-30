const API_URL =
"http://127.0.0.1:8000/api/v1/troubleshoot";


export async function troubleshoot(query){

    const response = await fetch(API_URL,{
        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify({
            query:query
        })
    });


    if(!response.ok){
        throw new Error("Backend connection failed");
    }


    return await response.json();

}