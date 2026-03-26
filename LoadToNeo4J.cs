// Disclaimer : This is not production ready code. Created only for Proof Of Concept
using System;
using System.Threading.Tasks;
using Neo4j.Driver;

// Please install "dotnet add package Neo4j.Driver" before running this code.
namespace CollegeGraphExample
{
    public class CollegeGraphService : IDisposable
    {
        private readonly IDriver _driver;

        public CollegeGraphService(string uri, string username, string password)
        {
            _driver = GraphDatabase.Driver(uri, AuthTokens.Basic(username, password));
        }

        public async Task CreateDepartmentsWithForLoopAsync()
        {
            var departments = new[]
            {
                new { Code = "CSE",  Name = "Computer Science & Engineering", Location = "Block A" },
                new { Code = "ECE",  Name = "Electronics & Communication Engg", Location = "Block B" },
                new { Code = "MECH", Name = "Mechanical Engineering", Location = "Workshop" },
                new { Code = "CIVIL",Name = "Civil Engineering", Location = "Block C" }
            };

            await using var session = _driver.AsyncSession();

            foreach (var dept in departments)
            {
                await session.ExecuteWriteAsync(async tx =>
                {
                    await tx.RunAsync(@"
                        MERGE (d:Department {code: $code})
                        SET d.name = $name,
                            d.location = $location
                    ",
                    new
                    {
                        code = dept.Code,
                        name = dept.Name,
                        location = dept.Location
                    });
                });

                Console.WriteLine($"Created/updated department: {dept.Code}");
            }
        }

        public async Task CreateStudentsWithForLoopAsync()
        {
            var students = new[]
            {
                new { Roll = "20CS0101", Name = "Aarav Sharma",   Year = 3, Cgpa = 8.7,  Dept = "CSE"  },
                new { Roll = "20CS0127", Name = "Priya Patel",    Year = 3, Cgpa = 9.1,  Dept = "CSE"  },
                new { Roll = "21EC0089", Name = "Rahul Verma",    Year = 2, Cgpa = 7.4,  Dept = "ECE"  },
                new { Roll = "19ME0045", Name = "Neha Gupta",     Year = 4, Cgpa = 8.2,  Dept = "MECH" },
                new { Roll = "20CE0032", Name = "Karthik Reddy",  Year = 3, Cgpa = 6.0, Dept = "CIVIL"},
                new { Roll = "21CS0156", Name = "Ananya Iyer",    Year = 2, Cgpa = 9.4,  Dept = "CSE"  }
            };

            await using var session = _driver.AsyncSession();

            foreach (var stu in students)
            {
                await session.ExecuteWriteAsync(async tx =>
                {
                    // Step 1: Create / update the student
                    await tx.RunAsync(@"
                        MERGE (s:Student {rollNumber: $roll})
                        SET s.name = $name,
                            s.year = $year,
                            s.cgpa = $cgpa
                    ",
                    new
                    {
                        roll = stu.Roll,
                        name = stu.Name,
                        year = stu.Year,
                        cgpa = stu.Cgpa
                    });

                    // Step 2: Connect student → department
                    await tx.RunAsync(@"
                        MATCH (s:Student {rollNumber: $roll})
                        MATCH (d:Department {code: $deptCode})
                        MERGE (s)-[:BELONGS_TO]->(d)
                    ",
                    new
                    {
                        roll = stu.Roll,
                        deptCode = stu.Dept
                    });
                });

                Console.WriteLine($"Created/updated student: {stu.Roll} → {stu.Dept}");
            }
        }

        public async Task CreateSampleCollegeDataAsync()
        {
            Console.WriteLine("Creating departments...");
            await CreateDepartmentsWithForLoopAsync();

            Console.WriteLine("\nCreating students and relationships...");
            await CreateStudentsWithForLoopAsync();

            Console.WriteLine("\nDone.");
        }

        public void Dispose() => _driver?.Dispose();
    }

    // Usage
    class Program
    {
        static async Task Main()
        {
            const string uri = "Your Neo4J URL";
            const string username = "Neo4J UID";
            const string password = "Neo4J PWD";

            using var service = new CollegeGraphService(uri, username, password);
			
            await service.CreateSampleCollegeDataAsync();

            Console.WriteLine("\nYou can now visualize in Neo4j Browser:");
            Console.WriteLine("MATCH p=(:Student)-[:BELONGS_TO]->(:Department) RETURN p LIMIT 25");
        }
    }
}



/*

// Attaching Properties to relation .. optional
C#await tx.RunAsync(@"
    MATCH (s:Student {rollNumber: $roll})
    MATCH (d:Department {code: $deptCode})

    MERGE (s)-[r:BELONGS_TO]->(d)

    SET r += $props                     // merge all these properties in (update + add)

    ON CREATE SET 
        r.createdAt   = $now,
        r.createdBy   = $createdBy      // audit fields example

    ON MATCH SET
        r.updatedAt   = $now,
        r.updateCount = coalesce(r.updateCount, 0) + 1
",
new
{
    roll      = stu.Roll,
    deptCode  = stu.Dept,
    now       = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
    createdBy = "import-script-v2",
    props = new Dictionary<string, object>
    {
        { "enrollmentYear", 2023 },
        { "status",         "Active" },
        { "gradeAverage",   8.4 },
        { "programType",    "Regular" }
    }
});
 */
