// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module tb #(parameter int DSIZE=8, parameter int ASIZE=2);
 localparam int DEPTH=1<<ASIZE, MAX_TRANSFERS=4096;
 logic wclk=0,rclk=0,wrst_n=0,rrst_n=0,winc=0,rinc=0;
 logic [DSIZE-1:0] wdata='0,rdata;
 logic wfull,rempty;
 logic [DSIZE-1:0] expected [0:MAX_TRANSFERS-1];
 integer whalf=5,rhalf=7,wphase=0,rphase=0,seed=1,scenario=0;
 integer accepted_writes=0,accepted_reads=0,data_checks=0,target_writes=0;
 logic [31:0] wrng,rrng;
 async_fifo #(.DSIZE(DSIZE),.ASIZE(ASIZE)) dut(.*);

 function automatic logic [31:0] prng(input logic [31:0] state);
   logic feedback;
   begin
     feedback=state[31]^state[21]^state[1]^state[0];
     prng={state[30:0],feedback};
     if(prng==0) prng=32'h1;
   end
 endfunction

 initial begin
   void'($value$plusargs("WHALF=%d",whalf)); void'($value$plusargs("WPHASE=%d",wphase));
   #(wphase); forever #(whalf) wclk=~wclk;
 end
 initial begin
   void'($value$plusargs("RHALF=%d",rhalf)); void'($value$plusargs("RPHASE=%d",rphase));
   #(rphase); forever #(rhalf) rclk=~rclk;
 end
 initial begin #250000; $fatal(1,"WATCHDOG_FAILED"); end

 // Sequence counters keep checking independent of producer/consumer timing.
 always @(posedge wclk) if(wrst_n && winc && !wfull) begin
   if(accepted_writes>=MAX_TRANSFERS) $fatal(1,"SCOREBOARD_OVERFLOW_FAILED");
   expected[accepted_writes]=wdata;
   accepted_writes=accepted_writes+1;
 end
 always @(posedge rclk) if(rrst_n && rinc && !rempty) begin
   if(accepted_reads>=accepted_writes) $fatal(1,"SCOREBOARD_UNDERFLOW_FAILED");
   if(rdata!==expected[accepted_reads]) begin
     $display("DATA_MISMATCH index=%0d expected=%0h actual=%0h",accepted_reads,expected[accepted_reads],rdata);
     $fatal(1,"DATA_ORDER_FAILED");
   end
   accepted_reads=accepted_reads+1; data_checks=data_checks+1;
 end

 task automatic write_word(input logic [DSIZE-1:0] value);
   begin
     @(negedge wclk); while(wfull) @(negedge wclk);
     wdata=value; winc=1; @(negedge wclk); winc=0;
   end
 endtask
 task automatic read_word;
   begin
     @(negedge rclk); while(rempty) @(negedge rclk);
     rinc=1; @(negedge rclk); rinc=0;
   end
 endtask
 task automatic happy_path;
   begin
     write_word(DSIZE'(1)); write_word(DSIZE'(2));
     repeat(4) @(negedge rclk); read_word(); read_word();
   end
 endtask
 task automatic boundary_stress;
   integer round,i;
   begin
     for(round=0;round<4;round=round+1) begin
       for(i=0;i<DEPTH;i=i+1) write_word(DSIZE'(round*DEPTH+i));
       @(negedge wclk); while(!wfull) @(negedge wclk);
       wdata='1; winc=1; repeat(3) @(negedge wclk); winc=0;
       for(i=0;i<DEPTH;i=i+1) read_word();
       @(negedge rclk); while(!rempty) @(negedge rclk);
       rinc=1; repeat(3) @(negedge rclk); rinc=0;
     end
   end
 endtask
 task automatic concurrent_stress;
   integer wi,ri;
   logic [DSIZE-1:0] next_data;
   begin
     target_writes=DEPTH*12+17;
     fork
       begin
         for(wi=0;wi<target_writes*3 && accepted_writes<target_writes;wi=wi+1) begin
           @(negedge wclk); wrng=prng(wrng); winc=wrng[0]|wrng[3];
           next_data=DSIZE'(wrng^accepted_writes^(accepted_writes<<3));
           wdata=next_data;
         end
         while(accepted_writes<target_writes) begin
           @(negedge wclk); winc=1; next_data=DSIZE'(accepted_writes*13+seed);
           wdata=next_data;
         end
         winc=0;
       end
       begin
         for(ri=0;accepted_reads<target_writes;ri=ri+1) begin
           @(negedge rclk); rrng=prng(rrng); rinc=rrng[0]|rrng[2];
         end
         rinc=0;
       end
     join
   end
 endtask

 initial begin
   void'($value$plusargs("SEED=%d",seed)); void'($value$plusargs("SCENARIO=%d",scenario));
   wrng=32'(seed)^32'h9e3779b9; rrng=32'(seed)^32'h7f4a7c15;
   #1; wrst_n=1; rrst_n=1; #1; wrst_n=0; rrst_n=0;
   repeat(4) @(negedge wclk); wrst_n=1;
   repeat(3) @(negedge rclk); rrst_n=1;
   case(scenario)
     0: happy_path(); 1: boundary_stress(); 2: concurrent_stress();
     default: $fatal(1,"UNKNOWN_SCENARIO_FAILED");
   endcase
   repeat(5) @(negedge wclk); repeat(5) @(negedge rclk);
   if(accepted_writes!=accepted_reads || data_checks!=accepted_reads) begin
     $display("SCOREBOARD_COUNTS writes=%0d reads=%0d checks=%0d target=%0d",accepted_writes,accepted_reads,data_checks,target_writes);
     $fatal(1,"SCOREBOARD_COUNTS_FAILED");
   end
   if(scenario==1 && (dut.checks.blocked_writes==0 || dut.checks.blocked_reads==0 ||
      dut.checks.write_wraps<4 || dut.checks.read_wraps<4)) $fatal(1,"BOUNDARY_EXERCISE_FAILED");
   if(scenario==2 && accepted_reads!=target_writes) $fatal(1,"CONCURRENT_EXERCISE_FAILED");
   $display("EXERCISE scenario=%0d seed=%0d depth=%0d width=%0d writes=%0d reads=%0d blocked_writes=%0d blocked_reads=%0d write_wraps=%0d read_wraps=%0d",scenario,seed,DEPTH,DSIZE,accepted_writes,accepted_reads,dut.checks.blocked_writes,dut.checks.blocked_reads,dut.checks.write_wraps,dut.checks.read_wraps);
   $display("FIFO_ASSERTIONS_PASS"); $finish;
 end
endmodule
