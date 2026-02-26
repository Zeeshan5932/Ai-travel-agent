const express = require("express");
const bodyParser = require("body-parser");
const axios = require("axios");
const path = require("path");
const marked = require("marked");

const app = express();

// ✅ Tell Express exactly where views folder is
app.set("views", path.join(__dirname, "views"));
app.set("view engine", "ejs");

app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, "public")));

app.get("/", (req, res) => {
  res.render("index", { response: null });
});

app.post("/search", async (req, res) => {
  const query = req.body.query;

  try {
    const apiResponse = await axios.post("http://localhost:8000/travel", {
      query: query,
    });

    res.render("index", 
      { response: marked.parse(apiResponse.data.response) });
  } catch (error) {
    res.render("index", { response: "Error fetching travel data." });
  }
});

// JSON API used by the frontend JS (returns HTML fragment)
app.post("/api/search", async (req, res) => {
  const query = req.body.query || req.query.query;
  try {
    const apiResponse = await axios.post("http://localhost:8000/travel", {
      query: query,
    });
    const html = marked.parse(apiResponse.data.response || "");
    res.json({ success: true, html });
  } catch (error) {
    const msg = error?.response?.data || error.message || "Unknown error";
    res.status(500).json({ success: false, error: String(msg) });
  }
});

app.listen(3000, () => {
  console.log("Frontend running at http://localhost:3000");
});
