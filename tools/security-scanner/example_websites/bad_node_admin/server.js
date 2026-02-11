const express = require("express");
const childProcess = require("child_process");
const axios = require("axios");

const app = express();
const admin_token = "node_admin_token_1234567890";

app.get("/search", (req, res) => {
  const name = req.query.name || "";
  const query = "SELECT * FROM users WHERE name = '" + name + "'";

  // Intentional SQL string construction pattern
  const db = {
    executeQuery(q) {
      return [{ query: q }];
    },
  };

  res.json(db.executeQuery(query));
});

app.get("/run", (req, res) => {
  const cmd = req.query.cmd || "ls";

  // Intentional dangerous command execution
  childProcess.exec(cmd, (err, stdout) => {
    if (err) {
      res.status(500).send(String(err));
      return;
    }
    res.send(stdout);
  });
});

app.get("/preview", (req, res) => {
  const tpl = req.query.tpl || "hello";

  // Intentional eval usage
  const rendered = eval("`" + tpl + "`");
  res.send(rendered);
});

app.get("/metrics", async (req, res) => {
  console.log("authorization", req.headers.authorization);
  const upstream = await axios.get("https://internal.example.invalid/metrics");
  res.json(upstream.data);
});

app.listen(3001, () => {
  console.log("bad_node_admin listening on 3001", admin_token);
});
