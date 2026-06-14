// const express = require("express");
// const bodyParser = require("body-parser");
// const axios = require("axios");
// const path = require("path");
// const marked = require("marked");

// const app = express();

// // ✅ Tell Express exactly where views folder is
// app.set("views", path.join(__dirname, "views"));
// app.set("view engine", "ejs");

// app.use(bodyParser.urlencoded({ extended: true }));
// app.use(express.static(path.join(__dirname, "public")));

// app.get("/", (req, res) => {
//   res.render("index", { response: null });
// });

// app.post("/search", async (req, res) => {
//   const query = req.body.query;

//   try {
//     const apiResponse = await axios.post("http://localhost:8000/travel", {
//       query: query,
//     });

//     res.render("index", 
//       { response: marked.parse(apiResponse.data.response) });
//   } catch (error) {
//     res.render("index", { response: "Error fetching travel data." });
//   }
// });

// // JSON API used by the frontend JS (returns HTML fragment)
// app.post("/api/search", async (req, res) => {
//   const query = req.body.query || req.query.query;
//   try {
//     const apiResponse = await axios.post("http://localhost:8000/travel", {
//       query: query,
//     });
//     const html = marked.parse(apiResponse.data.response || "");
//     res.json({ success: true, html });
//   } catch (error) {
//     const msg = error?.response?.data || error.message || "Unknown error";
//     res.status(500).json({ success: false, error: String(msg) });
//   }
// });

// app.listen(3000, () => {
//   console.log("Frontend running at http://localhost:3000");
// });



const express = require("express");
const bodyParser = require("body-parser");
const axios = require("axios");
const path = require("path");
const marked = require("marked");

const app = express();
const PORT = 3000;
const BACKEND_URL = "http://localhost:8000";

// -----------------------------
// View Engine Setup
// -----------------------------
app.set("views", path.join(__dirname, "views"));
app.set("view engine", "ejs");

// -----------------------------
// Middleware
// -----------------------------
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, "public")));

// -----------------------------
// Safe Render Helper
// -----------------------------
function renderIndex(res, options = {}) {
  res.render("index", {
    data: options.data || null,
    response: options.response || null,
    error: options.error || null,
  });
}

// -----------------------------
// Routes
// -----------------------------

// Home
app.get("/", (req, res) => {
  renderIndex(res);
});

app.post("/travel", async (req, res) => {
  try {
    console.log('Frontend /travel called with body:', req.body);
    const apiResponse = await axios.post(`${BACKEND_URL}/travel`, {
      query: req.body.query,
    });

    const backendData = apiResponse.data;
    console.log('Backend /travel responded:', backendData && (backendData.type || Object.keys(backendData)).slice(0,5));

    if (backendData.data) {
      return res.json({
        type: "structured",
        data: backendData.data,
      });
    }

    if (backendData.response) {
      return res.json({
        type: "html",
        html: marked.parse(backendData.response),
      });
    }

    return res.status(500).json({ error: "Invalid backend response" });

  } catch (error) {
    return res.status(500).json({
      error: error.message,
    });
  }
});

app.post("/budget-analysis", async (req, res) => {
  try {
    const apiResponse = await axios.post(`${BACKEND_URL}/budget-analysis`, req.body);
    return res.json(apiResponse.data);
  } catch (error) {
    return res.status(500).json({ error: error.response?.data?.detail || error.message });
  }
});

app.post("/weather", async (req, res) => {
  try {
    const apiResponse = await axios.post(`${BACKEND_URL}/weather`, req.body);
    return res.json(apiResponse.data);
  } catch (error) {
    return res.status(500).json({ error: error.response?.data?.detail || error.message });
  }
});

app.post("/visa-info", async (req, res) => {
  try {
    const apiResponse = await axios.post(`${BACKEND_URL}/visa-info`, req.body);
    return res.json(apiResponse.data);
  } catch (error) {
    return res.status(500).json({ error: error.response?.data?.detail || error.message });
  }
});

app.listen(PORT, () => {
  console.log(`🚀 Frontend running at http://localhost:${PORT}`);
});