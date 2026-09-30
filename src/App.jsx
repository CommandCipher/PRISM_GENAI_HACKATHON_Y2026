import { useState } from "react";
import "./App.css";
import { troubleshoot } from "./api";


function App() {


  const [query, setQuery] = useState("");

  const [status, setStatus] = useState("idle");

  const [result, setResult] = useState(null);

  const [currentActionIndex, setCurrentActionIndex] = useState(0);

  const [errorMessage, setErrorMessage] = useState("");



  // SEND QUERY TO BACKEND

  async function handleSubmit() {


    if (!query.trim()) {
      setErrorMessage("Please describe your device problem.");
      return;
    }


    setStatus("loading");
    setErrorMessage("");
    setResult(null);
    setCurrentActionIndex(0);



    try {


      const data = await troubleshoot(query);


      console.log("Backend response:", data);



      // GET FIRST VALID CONTEXT FROM BACKEND

      const context = data?.response?.contexts?.[0];


      if (!context) {

        setResult(data);

        setStatus("no-path");

        return;

      }



      // STORE ONLY CONTEXT

      setResult(context);

      setStatus("result");



    }

    catch(error) {


      console.error(error);


      setErrorMessage(
        error.message ||
        "Could not connect to the troubleshooting engine."
      );


      setStatus("error");

    }

  }





  // GET ACTIONS

  const actions = result?.actions || [];



  const currentAction =
    actions[currentActionIndex];





  // USER PRESSES YES

  function handleYes(){

    setStatus("success");

  }





  // USER PRESSES NO

  function handleNo(){


    const nextIndex =
      currentActionIndex + 1;



    if(nextIndex < actions.length){

      setCurrentActionIndex(nextIndex);

    }

    else{

      setStatus("not-solved");

    }

  }







  // RESET

  function resetApp(){

    setQuery("");

    setResult(null);

    setCurrentActionIndex(0);

    setErrorMessage("");

    setStatus("idle");

  }





  return (

    <div className="app">


      <main className="container">


        {/* HEADER */}

        <div className="header">


          <div className="brand">

            SAMSUNG PRISM

          </div>



          <h1>

            Smart Guided Troubleshooter

          </h1>



          <p className="subtitle">

            Describe your Galaxy device problem in your own words.

          </p>


        </div>







        {/* INPUT */}


        {status==="idle" && (


        <section className="input-card">


          <label>

            What's happening with your device?

          </label>



          <textarea


            placeholder="Example: My touchscreen is not responding"


            value={query}


            onChange={(e)=>{

              setQuery(e.target.value);

              setErrorMessage("");

            }}


          />



          {errorMessage &&

          <p className="inline-error">

            {errorMessage}

          </p>

          }





          <div className="examples">


            <span>

              Try:

            </span>




            <button

            className="example-chip"

            onClick={()=>

            setQuery("My touchscreen is not responding")

            }

            >

            Touchscreen issue

            </button>




            <button

            className="example-chip"

            onClick={()=>

            setQuery("My phone battery drains very quickly")

            }

            >

            Battery drains fast

            </button>





          </div>






          <button

          className="primary-button"

          onClick={handleSubmit}

          >

          Troubleshoot

          </button>



        </section>

        )}









        {/* LOADING */}



        {
        status==="loading" &&

        <section className="state-card">


          <div className="loader"></div>


          <h2>

          Analyzing your complaint

          </h2>


          <p>

          Finding validated troubleshooting steps...

          </p>


        </section>

        }









        {/* RESULT */}



        {
        status==="result" && currentAction &&


        <section className="result-card">



          <div className="result-header">


            <div>


              <p className="small-label">

              UNDERSTOOD ISSUE

              </p>



              <h2>

              {result.title}

              </h2>


            </div>





            {
            result.score &&

            <span className="confidence">

            {Math.round(result.score*100)}
            % confidence

            </span>

            }



          </div>







          <div className="progress-text">


          Step {currentActionIndex+1}

          {" of "}

          {actions.length}


          </div>







          <div className="action-card">


          <h3>

          {currentAction.actionName}

          </h3>




          <p>

          {currentAction.description}

          </p>







          {/* FIXED STEPS PATH */}

          {

          currentAction.stepGroups?.[0]?.steps &&


          <div className="steps">


          {

          currentAction.stepGroups[0].steps.map(

          (step,index)=>(


          <div className="step" key={index}>


          <div className="step-number">

          {index+1}

          </div>



          <div>

          {step}

          </div>



          </div>


          )


          )

          }


          </div>


          }






          </div>








          <div className="feedback">


          <h3>

          Did this fix the problem?

          </h3>



          <div className="feedback-buttons">


          <button

          className="yes-button"

          onClick={handleYes}

          >

          Yes

          </button>





          <button

          className="no-button"

          onClick={handleNo}

          >

          No

          </button>


          </div>



          </div>





        </section>


        }








        {/* SUCCESS */}



        {
        status==="success" &&


        <section className="state-card">


        <h2>

        Problem solved ✓

        </h2>


        <button

        className="primary-button"

        onClick={resetApp}

        >

        Troubleshoot another issue

        </button>


        </section>

        }








        {/* ERROR */}


        {
        status==="error" &&


        <section className="state-card">


        <h2>

        Something went wrong

        </h2>


        <p>

        {errorMessage}

        </p>



        <button

        className="primary-button"

        onClick={handleSubmit}

        >

        Try again

        </button>


        </section>

        }





        {/* NO PATH */}


        {
        status==="no-path" &&


        <section className="state-card">


        <h2>

        No validated troubleshooting path

        </h2>



        <button

        className="primary-button"

        onClick={resetApp}

        >

        Try again

        </button>



        </section>

        }



      </main>


    </div>

  );


}


export default App;